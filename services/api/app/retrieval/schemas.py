import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChunkDraft(BaseModel):
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    chunk_type: Literal["text", "table"]
    content: str = Field(min_length=1)
    token_count: int = Field(ge=1)


class RetrievedChunk(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    chunk_index: int
    chunk_type: Literal["text", "table"]
    content: str
    retrieval_score: float = Field(ge=0, le=1)
    rerank_score: float | None = Field(default=None, ge=0, le=1)
    relevance_score: float = Field(ge=0, le=1)


class IndexResult(BaseModel):
    document_id: uuid.UUID
    chunk_count: int
    retrieval_method: str


class SearchRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2_000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    chunks: list[RetrievedChunk]
