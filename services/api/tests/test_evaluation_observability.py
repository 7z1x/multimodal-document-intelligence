import json
import uuid
from pathlib import Path

import anyio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import RagRun
from app.agents.schemas import AgentResponse, AgentStep
from app.core.config import REPOSITORY_ROOT, Settings
from app.documents.models import Document, DocumentStatus
from app.evaluation.metrics import abstention_correctness, hit_at_k, id_context_precision
from app.evaluation.schemas import EvaluationRequest, JudgeScores
from app.evaluation.service import EvaluationService
from app.observability.redaction import redact
from app.observability.schemas import TraceExportPayload
from app.observability.service import ObservabilityService
from app.retrieval.models import DocumentChunk


class FakeJudge:
    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        reference_answer: str | None,
    ) -> JudgeScores:
        assert question
        assert answer
        assert contexts
        return JudgeScores(
            faithfulness=0.94,
            answer_correctness=0.91 if reference_answer else None,
            faithfulness_reason="Every claim appears in the supplied context.",
            answer_correctness_reason="The answer matches the reference.",
        )


class FakeExporter:
    def __init__(self) -> None:
        self.payloads: list[TraceExportPayload] = []

    async def export(self, payload: TraceExportPayload) -> str:
        self.payloads.append(payload)
        return "sent"


def make_document() -> Document:
    return Document(
        original_filename="invoice.pdf",
        stored_filename=f"{uuid.uuid4()}.pdf",
        media_type="application/pdf",
        size_bytes=1_024,
        page_count=1,
        sha256="b" * 64,
        status=DocumentStatus.INDEXED,
    )


def test_deterministic_evaluation_metrics_use_ranked_reference_ids() -> None:
    assert id_context_precision(["a", "b", "c"], {"a", "c"}) == pytest.approx(5 / 6)
    assert hit_at_k(["a", "b", "c"], {"c"}, 1) == 0
    assert hit_at_k(["a", "b", "c"], {"c"}, 3) == 1
    assert abstention_correctness("abstained", expected_answerable=False) == 1


def test_runtime_paths_resolve_from_repository_root() -> None:
    settings = Settings(
        storage_dir=Path("storage/documents"),
        audit_log_dir=Path("storage/audit-logs"),
    )

    assert settings.storage_dir == REPOSITORY_ROOT / "storage/documents"
    assert settings.audit_log_dir == REPOSITORY_ROOT / "storage/audit-logs"


@pytest.mark.asyncio
async def test_evaluation_service_persists_deterministic_and_judged_metrics(
    session: AsyncSession,
) -> None:
    document = make_document()
    session.add(document)
    await session.flush()
    chunk = DocumentChunk(
        document_id=document.id,
        page_number=1,
        chunk_index=0,
        chunk_type="text",
        content="Invoice INV-900 has a grand total of Rp 110.000,00.",
        token_count=10,
    )
    session.add(chunk)
    await session.flush()
    run = RagRun(
        document_id=document.id,
        question="What is the invoice total?",
        rewritten_query="invoice total",
        answer="The total is Rp 110.000,00.",
        citations=[{"chunk_id": str(chunk.id), "page_number": 1, "quote": "Rp 110.000,00"}],
        steps=[],
        retrieved_chunk_ids=[str(chunk.id)],
        retrieval_trace=[],
        status="answered",
        is_citation_verified=True,
        citation_support_score=1,
        citation_errors=[],
        latency_ms=900,
        trace_id=uuid.uuid4().hex,
        observability_status="disabled",
    )
    session.add(run)
    await session.commit()

    service = EvaluationService(session=session, judge=FakeJudge())
    result = await service.evaluate(
        document.id,
        run.id,
        EvaluationRequest(
            reference_answer="Rp 110.000,00",
            reference_chunk_ids=[chunk.id],
            expected_answerable=True,
        ),
    )

    assert result.passed is True
    assert {metric.metric_name for metric in result.metrics} == {
        "citation_match",
        "context_precision",
        "hit_at_1",
        "hit_at_3",
        "hit_at_5",
        "abstention_correctness",
        "latency_gate",
        "faithfulness",
        "answer_correctness",
    }
    assert (await service.batches(document.id))[0].batch_id == result.batch_id


def test_redaction_removes_secrets_email_and_long_numbers() -> None:
    redacted = redact(
        {
            "api_key": "should-not-appear",
            "message": "Send to finance@example.com account 123456789012",
        }
    )
    assert redacted == {
        "api_key": "[REDACTED]",
        "message": "Send to [REDACTED_EMAIL] account [REDACTED_NUMBER]",
    }


@pytest.mark.asyncio
async def test_observability_persists_redacted_event_and_json_log(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    document = make_document()
    session.add(document)
    await session.flush()
    run = RagRun(
        document_id=document.id,
        question="Email finance@example.com and account 123456789012",
        rewritten_query="invoice account",
        answer="Use account 123456789012.",
        citations=[],
        steps=[],
        retrieved_chunk_ids=[],
        retrieval_trace=[],
        status="answered",
        is_citation_verified=True,
        citation_support_score=1,
        citation_errors=[],
        latency_ms=120,
        trace_id=uuid.uuid4().hex,
        observability_status="pending",
    )
    session.add(run)
    await session.commit()
    response = AgentResponse(
        run_id=run.id,
        trace_id=run.trace_id,
        document_id=document.id,
        question=run.question,
        rewritten_query=run.rewritten_query,
        answer=run.answer,
        citations=[],
        status="answered",
        is_citation_verified=True,
        citation_support_score=1,
        citation_errors=[],
        attempts=1,
        latency_ms=run.latency_ms,
        steps=[AgentStep(node="generate", outcome="answer", detail="citations=0", duration_ms=50)],
        retrieved_chunks=[],
        retrieval_trace=[],
        observability_status="pending",
    )
    exporter = FakeExporter()
    service = ObservabilityService(
        session=session,
        exporter=exporter,
        audit_log_dir=tmp_path,
    )

    assert await service.record_rag_run(run, response) == "sent"
    events = await service.events(document.id)

    assert events[0].export_status == "sent"
    assert "finance@example.com" not in json.dumps(events[0].payload)
    assert "123456789012" not in json.dumps(events[0].payload)
    assert exporter.payloads[0].trace_id == run.trace_id
    log_files = [path async for path in anyio.Path(tmp_path).glob("audit-*.jsonl")]
    assert len(log_files) == 1
    assert "[REDACTED_NUMBER]" in await log_files[0].read_text(encoding="utf-8")
