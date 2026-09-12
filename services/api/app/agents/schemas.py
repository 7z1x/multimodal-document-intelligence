import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.generation.schemas import Citation
from app.retrieval.schemas import RetrievedChunk


class AgentStep(BaseModel):
    node: str
    outcome: str
    detail: str
    duration_ms: int = 0


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)


class RetrievalTraceItem(BaseModel):
    chunk_id: uuid.UUID
    page_number: int
    retrieval_score: float
    rerank_score: float | None
    final_relevance_score: float


class AgentResponse(BaseModel):
    run_id: uuid.UUID | None = None
    trace_id: str | None = None
    document_id: uuid.UUID
    question: str
    rewritten_query: str
    answer: str
    citations: list[Citation]
    status: Literal["answered", "abstained"]
    is_citation_verified: bool
    citation_support_score: float
    citation_errors: list[str]
    attempts: int
    latency_ms: int
    steps: list[AgentStep]
    retrieved_chunks: list[RetrievedChunk]
    retrieval_trace: list[RetrievalTraceItem]
    observability_status: str = "disabled"


class RagRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    question: str
    rewritten_query: str
    answer: str
    citations: list[Citation]
    steps: list[AgentStep]
    status: Literal["answered", "abstained"]
    is_citation_verified: bool
    citation_support_score: float
    citation_errors: list[str]
    latency_ms: int
    trace_id: str
    observability_status: str
    retrieved_chunk_ids: list[str]
    retrieval_trace: list[RetrievalTraceItem]
    created_at: datetime
