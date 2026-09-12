from typing import Protocol

from app.evaluation.schemas import JudgeScores


class EvaluationJudge(Protocol):
    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        reference_answer: str | None,
    ) -> JudgeScores: ...
