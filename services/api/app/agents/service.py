import uuid
from time import perf_counter
from typing import Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import RagRun
from app.agents.schemas import AgentResponse, AgentStep, RagRunRead
from app.core.exceptions import AppError
from app.documents.models import Document, DocumentStatus
from app.generation.base import RagModel
from app.generation.citations import verify_citations
from app.generation.schemas import GeneratedAnswer
from app.retrieval.base import Retriever
from app.retrieval.schemas import RetrievedChunk


class AgentState(TypedDict, total=False):
    document_id: uuid.UUID
    question: str
    rewritten_query: str
    attempt: int
    contexts: list[RetrievedChunk]
    sufficient: bool
    generated: GeneratedAnswer
    citation_verified: bool
    steps: list[AgentStep]


class AgenticRagService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        retriever: Retriever,
        model: RagModel,
        top_k: int,
        min_relevance: float,
        max_attempts: int,
    ) -> None:
        self.session = session
        self.retriever = retriever
        self.model = model
        self.top_k = top_k
        self.min_relevance = min_relevance
        self.max_attempts = max_attempts
        self.graph = self._build_graph()

    def _build_graph(
        self,
    ) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
        builder = StateGraph(AgentState)
        builder.add_node("rewrite", self._rewrite)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("evaluate_context", self._evaluate_context)
        builder.add_node("prepare_retry", self._prepare_retry)
        builder.add_node("generate", self._generate)
        builder.add_node("verify_citations", self._verify_citations)
        builder.add_node("abstain", self._abstain)
        builder.add_edge(START, "rewrite")
        builder.add_edge("rewrite", "retrieve")
        builder.add_edge("retrieve", "evaluate_context")
        builder.add_conditional_edges(
            "evaluate_context",
            self._route_after_evaluation,
            {"generate": "generate", "retry": "prepare_retry", "abstain": "abstain"},
        )
        builder.add_edge("prepare_retry", "rewrite")
        builder.add_edge("generate", "verify_citations")
        builder.add_conditional_edges(
            "verify_citations",
            self._route_after_verification,
            {"done": END, "retry": "prepare_retry", "abstain": "abstain"},
        )
        builder.add_edge("abstain", END)
        return builder.compile()

    async def ask(self, document_id: uuid.UUID, question: str) -> AgentResponse:
        document = await self.session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        if document.status != DocumentStatus.INDEXED:
            raise AppError(
                code="DOCUMENT_NOT_INDEXED",
                message="Buat indeks RAG dokumen sebelum mengajukan pertanyaan",
                status_code=409,
            )
        response = await self.execute(document_id, question)
        run = RagRun(
            document_id=document_id,
            question=question,
            rewritten_query=response.rewritten_query,
            answer=response.answer,
            citations=[citation.model_dump(mode="json") for citation in response.citations],
            steps=[step.model_dump(mode="json") for step in response.steps],
            retrieved_chunk_ids=[str(chunk.id) for chunk in response.retrieved_chunks],
            status=response.status,
            is_citation_verified=response.is_citation_verified,
            latency_ms=response.latency_ms,
        )
        self.session.add(run)
        await self.session.commit()
        response.run_id = run.id
        return response

    async def execute(self, document_id: uuid.UUID, question: str) -> AgentResponse:
        started = perf_counter()
        initial: AgentState = {
            "document_id": document_id,
            "question": question,
            "attempt": 0,
            "steps": [],
        }
        final = cast(
            AgentState,
            await self.graph.ainvoke(initial, {"recursion_limit": self.max_attempts * 8 + 4}),
        )
        generated = final["generated"]
        verified = final.get("citation_verified", False)
        status: Literal["answered", "abstained"] = (
            "answered" if generated.can_answer and verified else "abstained"
        )
        return AgentResponse(
            document_id=document_id,
            question=question,
            rewritten_query=final.get("rewritten_query", question),
            answer=generated.answer,
            citations=generated.citations if status == "answered" else [],
            status=status,
            is_citation_verified=verified if status == "answered" else False,
            attempts=final.get("attempt", 0) + 1,
            latency_ms=round((perf_counter() - started) * 1000),
            steps=final.get("steps", []),
            retrieved_chunks=final.get("contexts", []),
        )

    async def runs(self, document_id: uuid.UUID) -> list[RagRunRead]:
        rows = list(
            (
                await self.session.scalars(
                    select(RagRun)
                    .where(RagRun.document_id == document_id)
                    .order_by(RagRun.created_at.desc())
                )
            ).all()
        )
        return [RagRunRead.model_validate(row) for row in rows]

    async def _rewrite(self, state: AgentState) -> AgentState:
        attempt = state.get("attempt", 0)
        query = await self.model.rewrite(state["question"], attempt)
        return {
            "rewritten_query": query,
            "steps": self._step(state, "rewrite", "ok", f"attempt={attempt + 1}"),
        }

    async def _retrieve(self, state: AgentState) -> AgentState:
        contexts = await self.retriever.search(
            state["document_id"],
            state["rewritten_query"],
            self.top_k,
        )
        return {
            "contexts": contexts,
            "steps": self._step(state, "retrieve", "ok", f"chunks={len(contexts)}"),
        }

    async def _evaluate_context(self, state: AgentState) -> AgentState:
        contexts = state.get("contexts", [])
        sufficient = any(chunk.relevance_score >= self.min_relevance for chunk in contexts)
        return {
            "sufficient": sufficient,
            "steps": self._step(
                state,
                "evaluate_context",
                "sufficient" if sufficient else "insufficient",
                f"threshold={self.min_relevance}",
            ),
        }

    def _route_after_evaluation(self, state: AgentState) -> Literal["generate", "retry", "abstain"]:
        if state.get("sufficient", False):
            return "generate"
        if state.get("attempt", 0) + 1 < self.max_attempts:
            return "retry"
        return "abstain"

    async def _generate(self, state: AgentState) -> AgentState:
        generated = await self.model.generate(state["question"], state.get("contexts", []))
        return {
            "generated": generated,
            "steps": self._step(
                state,
                "generate",
                "answer" if generated.can_answer else "cannot_answer",
                f"citations={len(generated.citations)}",
            ),
        }

    async def _verify_citations(self, state: AgentState) -> AgentState:
        verified = verify_citations(state["generated"], state.get("contexts", []))
        return {
            "citation_verified": verified,
            "steps": self._step(
                state,
                "verify_citations",
                "verified" if verified else "rejected",
                "deterministic chunk, page, and quote check",
            ),
        }

    def _route_after_verification(self, state: AgentState) -> Literal["done", "retry", "abstain"]:
        if state.get("citation_verified", False):
            return "done"
        if state.get("attempt", 0) + 1 < self.max_attempts:
            return "retry"
        return "abstain"

    async def _prepare_retry(self, state: AgentState) -> AgentState:
        next_attempt = state.get("attempt", 0) + 1
        return {
            "attempt": next_attempt,
            "steps": self._step(state, "prepare_retry", "retry", f"attempt={next_attempt + 1}"),
        }

    async def _abstain(self, state: AgentState) -> AgentState:
        return {
            "generated": GeneratedAnswer(
                can_answer=False,
                answer=(
                    "Informasi yang diminta tidak ditemukan dengan bukti yang cukup "
                    "di dalam dokumen ini."
                ),
                citations=[],
            ),
            "citation_verified": False,
            "steps": self._step(
                state,
                "abstain",
                "safe_stop",
                "maximum retrieval attempts reached",
            ),
        }

    @staticmethod
    def _step(
        state: AgentState,
        node: str,
        outcome: str,
        detail: str,
    ) -> list[AgentStep]:
        return [*state.get("steps", []), AgentStep(node=node, outcome=outcome, detail=detail)]
