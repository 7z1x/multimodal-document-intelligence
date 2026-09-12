import uuid

from pydantic import BaseModel, Field, field_validator


class ChunkRanking(BaseModel):
    chunk_id: uuid.UUID
    relevance_score: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)

    @field_validator("rationale")
    @classmethod
    def limit_rationale(cls, value: str) -> str:
        if len(value) > 300:
            raise ValueError("ranking rationale must not exceed 300 characters")
        return value


class RerankingResult(BaseModel):
    rankings: list[ChunkRanking] = Field(min_length=1, max_length=20)
