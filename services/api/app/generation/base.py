from typing import Protocol

from app.generation.schemas import GeneratedAnswer
from app.retrieval.schemas import RetrievedChunk


class RagModel(Protocol):
    async def rewrite(self, question: str, attempt: int) -> str: ...

    async def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
    ) -> GeneratedAnswer: ...
