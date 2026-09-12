import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import RagRun
from app.core.exceptions import AppError
from app.documents.models import Document
from app.evaluation.base import EvaluationJudge
from app.evaluation.metrics import abstention_correctness, hit_at_k, id_context_precision
from app.evaluation.models import EvaluationRun
from app.evaluation.schemas import (
    EvaluationBatchRead,
    EvaluationMetricRead,
    EvaluationRequest,
)
from app.retrieval.models import DocumentChunk

THRESHOLDS = {
    "citation_match": 0.85,
    "context_precision": 0.75,
    "hit_at_1": 0.65,
    "hit_at_3": 0.80,
    "hit_at_5": 0.90,
    "faithfulness": 0.82,
    "answer_correctness": 0.80,
    "abstention_correctness": 0.90,
    "latency_gate": 1.0,
}


class EvaluationService:
    def __init__(self, *, session: AsyncSession, judge: EvaluationJudge) -> None:
        self.session = session
        self.judge = judge

    async def evaluate(
        self,
        document_id: uuid.UUID,
        rag_run_id: uuid.UUID,
        request: EvaluationRequest,
    ) -> EvaluationBatchRead:
        await self._ensure_document(document_id)
        run = await self.session.scalar(
            select(RagRun).where(
                RagRun.id == rag_run_id,
                RagRun.document_id == document_id,
            )
        )
        if run is None:
            raise AppError(
                code="RAG_RUN_NOT_FOUND",
                message="RAG run tidak ditemukan untuk dokumen ini",
                status_code=404,
            )

        retrieved_ids = [str(item) for item in run.retrieved_chunk_ids]
        citation_ids = {
            str(citation.get("chunk_id"))
            for citation in run.citations
            if citation.get("chunk_id") is not None
        }
        explicit_reference_ids = {str(item) for item in request.reference_chunk_ids}
        reference_ids = explicit_reference_ids or citation_ids
        reference_source = "ground_truth" if explicit_reference_ids else "verified_citations_proxy"
        metric_rows: list[EvaluationRun] = []
        batch_id = uuid.uuid4()

        if run.status == "answered":
            metric_rows.append(
                self._metric(
                    batch_id=batch_id,
                    run=run,
                    name="citation_match",
                    score=run.citation_support_score,
                    evaluation_type="deterministic",
                    evaluator="exact-page-quote-verifier",
                    metadata={"citation_count": len(run.citations)},
                )
            )
            metric_rows.append(
                self._metric(
                    batch_id=batch_id,
                    run=run,
                    name="context_precision",
                    score=id_context_precision(retrieved_ids, reference_ids),
                    evaluation_type="deterministic",
                    evaluator="id-ranked-average-precision",
                    metadata={"reference_source": reference_source},
                )
            )

        if explicit_reference_ids:
            for k in (1, 3, 5):
                metric_rows.append(
                    self._metric(
                        batch_id=batch_id,
                        run=run,
                        name=f"hit_at_{k}",
                        score=hit_at_k(retrieved_ids, explicit_reference_ids, k),
                        evaluation_type="deterministic",
                        evaluator="retrieval-id-match",
                        metadata={"k": k, "reference_chunk_count": len(explicit_reference_ids)},
                    )
                )

        if request.expected_answerable is not None:
            metric_rows.append(
                self._metric(
                    batch_id=batch_id,
                    run=run,
                    name="abstention_correctness",
                    score=abstention_correctness(run.status, request.expected_answerable),
                    evaluation_type="deterministic",
                    evaluator="expected-answerability-match",
                    metadata={"expected_answerable": request.expected_answerable},
                )
            )

        metric_rows.append(
            self._metric(
                batch_id=batch_id,
                run=run,
                name="latency_gate",
                score=float(run.latency_ms <= 6_000),
                evaluation_type="deterministic",
                evaluator="wall-clock-threshold",
                metadata={"latency_ms": run.latency_ms, "maximum_ms": 6_000},
            )
        )

        contexts = await self._contexts(document_id, retrieved_ids)
        if request.include_llm_judge and run.status == "answered" and contexts:
            judged = await self.judge.score(
                question=run.question,
                answer=run.answer,
                contexts=contexts,
                reference_answer=request.reference_answer,
            )
            metric_rows.append(
                self._metric(
                    batch_id=batch_id,
                    run=run,
                    name="faithfulness",
                    score=judged.faithfulness,
                    evaluation_type="llm_as_judge",
                    evaluator="opencode-muse-structured",
                    metadata={"reason": judged.faithfulness_reason},
                )
            )
            if judged.answer_correctness is not None and request.reference_answer:
                metric_rows.append(
                    self._metric(
                        batch_id=batch_id,
                        run=run,
                        name="answer_correctness",
                        score=judged.answer_correctness,
                        evaluation_type="llm_as_judge",
                        evaluator="opencode-muse-structured",
                        metadata={"reason": judged.answer_correctness_reason or ""},
                    )
                )

        self.session.add_all(metric_rows)
        await self.session.commit()
        return self._batch(metric_rows)

    async def batches(self, document_id: uuid.UUID) -> list[EvaluationBatchRead]:
        await self._ensure_document(document_id)
        rows = list(
            (
                await self.session.scalars(
                    select(EvaluationRun)
                    .where(EvaluationRun.document_id == document_id)
                    .order_by(EvaluationRun.created_at.desc(), EvaluationRun.metric_name)
                )
            ).all()
        )
        grouped: dict[uuid.UUID, list[EvaluationRun]] = defaultdict(list)
        for row in rows:
            grouped[row.batch_id].append(row)
        return [self._batch(items) for items in grouped.values()]

    async def _ensure_document(self, document_id: uuid.UUID) -> None:
        if await self.session.scalar(select(Document.id).where(Document.id == document_id)) is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )

    async def _contexts(self, document_id: uuid.UUID, ids: list[str]) -> list[str]:
        if not ids:
            return []
        parsed_ids = [uuid.UUID(item) for item in ids]
        chunks = list(
            (
                await self.session.scalars(
                    select(DocumentChunk).where(
                        DocumentChunk.document_id == document_id,
                        DocumentChunk.id.in_(parsed_ids),
                    )
                )
            ).all()
        )
        by_id = {str(chunk.id): chunk.content for chunk in chunks}
        return [by_id[item] for item in ids if item in by_id]

    @staticmethod
    def _metric(
        *,
        batch_id: uuid.UUID,
        run: RagRun,
        name: str,
        score: float,
        evaluation_type: str,
        evaluator: str,
        metadata: dict[str, object],
    ) -> EvaluationRun:
        normalized = max(0.0, min(1.0, score))
        threshold = THRESHOLDS[name]
        return EvaluationRun(
            batch_id=batch_id,
            document_id=run.document_id,
            rag_run_id=run.id,
            metric_name=name,
            score=normalized,
            evaluation_type=evaluation_type,
            evaluator=evaluator,
            threshold=threshold,
            passed=normalized >= threshold,
            metadata_json=metadata,
        )

    @staticmethod
    def _batch(rows: list[EvaluationRun]) -> EvaluationBatchRead:
        scores = [row.score for row in rows]
        return EvaluationBatchRead(
            batch_id=rows[0].batch_id,
            document_id=rows[0].document_id,
            rag_run_id=rows[0].rag_run_id,
            overall_score=sum(scores) / len(scores),
            passed=all(row.passed for row in rows),
            metrics=[
                EvaluationMetricRead(
                    id=row.id,
                    metric_name=row.metric_name,
                    score=row.score,
                    evaluation_type=row.evaluation_type,
                    evaluator=row.evaluator,
                    threshold=row.threshold,
                    passed=row.passed,
                    metadata=row.metadata_json,
                )
                for row in rows
            ],
            created_at=rows[0].created_at,
        )
