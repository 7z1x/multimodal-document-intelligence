import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    reference_answer: str | None = Field(default=None, max_length=4_000)
    reference_chunk_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)
    expected_answerable: bool | None = None
    include_llm_judge: bool = True


class JudgeScores(BaseModel):
    faithfulness: float = Field(ge=0, le=1)
    answer_correctness: float | None = Field(default=None, ge=0, le=1)
    faithfulness_reason: str = Field(min_length=1, max_length=500)
    answer_correctness_reason: str | None = Field(default=None, max_length=500)


class EvaluationMetricRead(BaseModel):
    id: uuid.UUID
    metric_name: str
    score: float
    evaluation_type: str
    evaluator: str
    threshold: float
    passed: bool
    metadata: dict[str, object]


class EvaluationBatchRead(BaseModel):
    batch_id: uuid.UUID
    document_id: uuid.UUID
    rag_run_id: uuid.UUID
    overall_score: float
    passed: bool
    metrics: list[EvaluationMetricRead]
    created_at: datetime
