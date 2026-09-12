import uuid

from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    chunk_id: uuid.UUID
    page_number: int = Field(ge=1)
    quote: str = Field(min_length=1)

    @field_validator("quote")
    @classmethod
    def limit_quote_length(cls, value: str) -> str:
        if len(value) > 500:
            raise ValueError("citation quote must not exceed 500 characters")
        return value


class RewrittenQuery(BaseModel):
    query: str = Field(min_length=2)

    @field_validator("query")
    @classmethod
    def limit_query_length(cls, value: str) -> str:
        if len(value) > 2_000:
            raise ValueError("rewritten query must not exceed 2000 characters")
        return value


class GeneratedAnswer(BaseModel):
    can_answer: bool
    answer: str = Field(min_length=1)
    citations: list[Citation] = Field(default_factory=list, max_length=10)

    @field_validator("answer")
    @classmethod
    def limit_answer_length(cls, value: str) -> str:
        if len(value) > 8_000:
            raise ValueError("answer must not exceed 8000 characters")
        return value


class CitationVerification(BaseModel):
    valid: bool
    total_citations: int = Field(ge=0)
    supported_citations: int = Field(ge=0)
    support_score: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)
