import json
import uuid
from pathlib import Path
from typing import cast

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.service import AgenticRagService
from app.documents.models import Document, DocumentStatus
from app.documents.page_models import DocumentPage
from app.generation.citations import verify_citation_support, verify_citations
from app.generation.schemas import Citation, GeneratedAnswer
from app.providers.opencode import OpenCodeStructuredClient
from app.reranking.opencode import OpenCodeReranker
from app.retrieval.chunking import PageAwareChunker
from app.retrieval.repository import PostgresTextChunkRepository
from app.retrieval.schemas import ChunkDraft, RetrievedChunk
from app.retrieval.service import DocumentIndexingService


class FakeRepository:
    def __init__(self) -> None:
        self.document_id: uuid.UUID | None = None
        self.chunks: list[ChunkDraft] = []

    async def replace(
        self,
        document_id: uuid.UUID,
        chunks: list[ChunkDraft],
    ) -> None:
        self.document_id = document_id
        self.chunks = chunks

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        return []


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.queries: list[str] = []

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        self.queries.append(query)
        return self.chunks[:limit]


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0

    async def rerank(
        self,
        question: str,
        contexts: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        self.calls += 1
        return [
            chunk.model_copy(
                update={
                    "rerank_score": chunk.relevance_score,
                    "relevance_score": chunk.relevance_score,
                }
            )
            for chunk in contexts
        ]


class FakeRagModel:
    def __init__(self, answer: GeneratedAnswer | None = None) -> None:
        self.answer = answer
        self.rewrite_attempts: list[int] = []

    async def rewrite(self, question: str, attempt: int) -> str:
        self.rewrite_attempts.append(attempt)
        return f"{question} semantic attempt {attempt + 1}"

    async def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
    ) -> GeneratedAnswer:
        assert self.answer is not None
        return self.answer


def make_document(status: DocumentStatus) -> Document:
    return Document(
        original_filename="invoice.pdf",
        stored_filename=f"{uuid.uuid4()}.pdf",
        media_type="application/pdf",
        size_bytes=1_024,
        page_count=1,
        sha256="a" * 64,
        status=status,
    )


def make_chunk(document_id: uuid.UUID, *, relevance_score: float = 0.91) -> RetrievedChunk:
    return RetrievedChunk(
        id=uuid.uuid4(),
        document_id=document_id,
        page_number=1,
        chunk_index=0,
        chunk_type="text",
        content="Invoice Number: INV-900. Grand Total: Rp 110.000,00.",
        retrieval_score=relevance_score,
        relevance_score=relevance_score,
    )


def test_page_aware_chunker_preserves_page_and_table_boundaries() -> None:
    page = DocumentPage(
        document_id=uuid.uuid4(),
        page_number=2,
        extraction_method="ocr",
        text="Invoice header\n" + ("Long invoice description. " * 20),
        character_count=520,
        layout_json={"tables": [{"text": "Item | Qty | Total\nCoffee | 2 | 50000"}]},
    )

    chunks = PageAwareChunker(chunk_size=160, chunk_overlap=20).split([page])

    assert len(chunks) > 2
    assert all(chunk.page_number == 2 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert any(chunk.chunk_type == "table" for chunk in chunks)
    assert any("Coffee" in chunk.content for chunk in chunks)


@pytest.mark.asyncio
async def test_text_repository_returns_document_scoped_relevance(session: AsyncSession) -> None:
    first = make_document(DocumentStatus.INDEXED)
    second = make_document(DocumentStatus.INDEXED)
    session.add_all([first, second])
    await session.flush()
    repository = PostgresTextChunkRepository(session)
    await repository.replace(
        first.id,
        [
            ChunkDraft(
                page_number=1,
                chunk_index=0,
                chunk_type="text",
                content="Invoice INV-900 has grand total Rp 110.000.",
                token_count=10,
            )
        ],
    )
    await repository.replace(
        second.id,
        [
            ChunkDraft(
                page_number=1,
                chunk_index=0,
                chunk_type="text",
                content="Invoice INV-900 has grand total Rp 999.000.",
                token_count=10,
            )
        ],
    )
    await session.commit()

    results = await repository.search(first.id, "total INV-900", 5)

    assert len(results) == 1
    assert results[0].document_id == first.id
    assert results[0].relevance_score == 1.0


@pytest.mark.asyncio
async def test_opencode_client_disables_tools_and_validates_json() -> None:
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            return httpx.Response(200, json=True)
        body = json.loads(request.content)
        captured.append(body)
        if request.url.path == "/session":
            return httpx.Response(200, json={"id": "ses_test"})
        return httpx.Response(
            200,
            json={
                "info": {"role": "assistant"},
                "parts": [{"type": "text", "text": '{"query":"invoice total"}'}],
            },
        )

    client = OpenCodeStructuredClient(
        base_url="http://opencode.test",
        provider="opencode",
        model="muse-spark-1.3-contributor-free",
        directory=Path("."),
        timeout_seconds=10,
        transport=httpx.MockTransport(handler),
    )

    from app.generation.schemas import RewrittenQuery

    result = await client.generate(
        RewrittenQuery,
        system="Return JSON",
        prompt="rewrite this",
        title="test",
    )

    assert result.query == "invoice total"
    assert captured[0]["permission"] == [
        {"permission": "*", "pattern": "*", "action": "deny"}
    ]
    assert captured[1]["tools"]
    assert all(enabled is False for enabled in captured[1]["tools"].values())


@pytest.mark.asyncio
async def test_opencode_reranker_reorders_and_preserves_retrieval_score() -> None:
    document_id = uuid.uuid4()
    first = make_chunk(document_id, relevance_score=0.9)
    second = make_chunk(document_id, relevance_score=0.2).model_copy(
        update={"id": uuid.uuid4(), "chunk_index": 1}
    )

    class FakeRankingClient:
        async def generate(self, schema: type[object], **_: object) -> object:
            return schema.model_validate(  # type: ignore[attr-defined,no-any-return]
                {
                    "rankings": [
                        {
                            "chunk_id": str(first.id),
                            "relevance_score": 0.1,
                            "rationale": "Does not answer the question",
                        },
                        {
                            "chunk_id": str(second.id),
                            "relevance_score": 0.95,
                            "rationale": "Contains the requested evidence",
                        },
                    ]
                }
            )

    reranker = OpenCodeReranker(
        cast(OpenCodeStructuredClient, FakeRankingClient()),
        model_weight=0.65,
    )
    results = await reranker.rerank("What is the requested evidence?", [first, second])

    assert [item.id for item in results] == [second.id, first.id]
    assert results[0].retrieval_score == 0.2
    assert results[0].rerank_score == 0.95
    assert results[0].relevance_score == pytest.approx(0.6875)


@pytest.mark.asyncio
async def test_indexing_service_builds_chunks_and_marks_document_indexed(
    session: AsyncSession,
) -> None:
    document = make_document(DocumentStatus.STRUCTURE_EXTRACTED)
    session.add(document)
    await session.flush()
    session.add(
        DocumentPage(
            document_id=document.id,
            page_number=1,
            extraction_method="native",
            text="Invoice Number: INDEX-001\nGrand Total: Rp 110.000,00",
            character_count=55,
            layout_json={},
        )
    )
    await session.commit()
    repository = FakeRepository()
    service = DocumentIndexingService(
        session=session,
        chunker=PageAwareChunker(chunk_size=200, chunk_overlap=20),
        repository=repository,
    )

    result = await service.index(document.id)

    assert result.chunk_count == 1
    assert result.retrieval_method == "postgresql-full-text"
    assert document.status == DocumentStatus.INDEXED
    assert repository.document_id == document.id


def test_citation_verifier_checks_chunk_page_and_exact_quote() -> None:
    document_id = uuid.uuid4()
    chunk = make_chunk(document_id)
    answer = GeneratedAnswer(
        can_answer=True,
        answer="Nomor invoice adalah INV-900.",
        citations=[Citation(chunk_id=chunk.id, page_number=1, quote="Invoice Number: INV-900")],
    )

    assert verify_citations(answer, [chunk]) is True
    invalid = answer.model_copy(
        update={
            "citations": [
                Citation(chunk_id=chunk.id, page_number=2, quote="Invoice Number: INV-900")
            ]
        }
    )
    assert verify_citations(invalid, [chunk]) is False
    verification = verify_citation_support(invalid, [chunk])
    assert verification.support_score == 0
    assert verification.errors == ["citation_0:page_mismatch"]


@pytest.mark.asyncio
async def test_agent_answers_only_after_citation_verification(session: AsyncSession) -> None:
    document_id = uuid.uuid4()
    chunk = make_chunk(document_id)
    model = FakeRagModel(
        GeneratedAnswer(
            can_answer=True,
            answer="Nomor invoice adalah INV-900.",
            citations=[Citation(chunk_id=chunk.id, page_number=1, quote="Invoice Number: INV-900")],
        )
    )
    service = AgenticRagService(
        session=session,
        retriever=FakeRetriever([chunk]),
        reranker=FakeReranker(),
        model=model,
        top_k=5,
        min_relevance=0.15,
        max_attempts=2,
    )

    result = await service.execute(document_id, "Berapa nomor invoice?")

    assert result.status == "answered"
    assert result.is_citation_verified is True
    assert result.citation_support_score == 1
    assert result.citation_errors == []
    assert result.retrieval_trace[0].rerank_score == pytest.approx(0.91)
    assert result.attempts == 1
    assert [step.node for step in result.steps] == [
        "rewrite",
        "retrieve",
        "rerank",
        "evaluate_context",
        "generate",
        "verify_citations",
    ]


@pytest.mark.asyncio
async def test_agent_retries_then_abstains_on_insufficient_context(
    session: AsyncSession,
) -> None:
    document_id = uuid.uuid4()
    retriever = FakeRetriever([make_chunk(document_id, relevance_score=0.05)])
    model = FakeRagModel()
    service = AgenticRagService(
        session=session,
        retriever=retriever,
        reranker=FakeReranker(),
        model=model,
        top_k=5,
        min_relevance=0.15,
        max_attempts=2,
    )

    result = await service.execute(document_id, "Siapa direktur vendor?")

    assert result.status == "abstained"
    assert result.attempts == 2
    assert model.rewrite_attempts == [0, 1]
    assert "prepare_retry" in [step.node for step in result.steps]
    assert result.steps[-1].node == "abstain"


@pytest.mark.asyncio
async def test_agent_rejects_unsupported_quote_then_abstains(session: AsyncSession) -> None:
    document_id = uuid.uuid4()
    chunk = make_chunk(document_id)
    model = FakeRagModel(
        GeneratedAnswer(
            can_answer=True,
            answer="Direkturnya adalah seseorang yang tidak tertulis.",
            citations=[
                Citation(
                    chunk_id=chunk.id,
                    page_number=1,
                    quote="Director: Unsupported Person",
                )
            ],
        )
    )
    service = AgenticRagService(
        session=session,
        retriever=FakeRetriever([chunk]),
        reranker=FakeReranker(),
        model=model,
        top_k=5,
        min_relevance=0.15,
        max_attempts=2,
    )

    result = await service.execute(document_id, "Siapa direktur vendor?")

    assert result.status == "abstained"
    assert result.attempts == 2
    assert [step.outcome for step in result.steps].count("rejected") == 2
    assert result.citations == []


@pytest.mark.asyncio
async def test_agent_ask_persists_readable_audit_run(session: AsyncSession) -> None:
    document = make_document(DocumentStatus.INDEXED)
    session.add(document)
    await session.commit()
    chunk = make_chunk(document.id)
    service = AgenticRagService(
        session=session,
        retriever=FakeRetriever([chunk]),
        reranker=FakeReranker(),
        model=FakeRagModel(
            GeneratedAnswer(
                can_answer=True,
                answer="Nomor invoice adalah INV-900.",
                citations=[
                    Citation(
                        chunk_id=chunk.id,
                        page_number=1,
                        quote="Invoice Number: INV-900",
                    )
                ],
            )
        ),
        top_k=5,
        min_relevance=0.15,
        max_attempts=2,
    )

    response = await service.ask(document.id, "Berapa nomor invoice?")
    runs = await service.runs(document.id)

    assert response.run_id is not None
    assert len(runs) == 1
    assert runs[0].id == response.run_id
    assert runs[0].citations[0].page_number == 1
    assert runs[0].citation_support_score == 1
    assert runs[0].citation_errors == []
    assert runs[0].retrieval_trace[0].rerank_score == pytest.approx(0.91)
    assert runs[0].steps[-1].node == "verify_citations"
