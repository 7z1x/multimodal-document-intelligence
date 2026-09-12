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


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)


class AgentResponse(BaseModel):
    run_id: uuid.UUID | None = None
    document_id: uuid.UUID
    question: str
    rewritten_query: str
    answer: str
    citations: list[Citation]
    status: Literal["answered", "abstained"]
    is_citation_verified: bool
    attempts: int
    latency_ms: int
    steps: list[AgentStep]
    retrieved_chunks: list[RetrievedChunk]


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
    latency_ms: int
    retrieved_chunk_ids: list[str]
    created_at: datetime
