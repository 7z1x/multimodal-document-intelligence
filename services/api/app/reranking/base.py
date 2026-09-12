from typing import Protocol

from app.retrieval.schemas import RetrievedChunk


class Reranker(Protocol):
    async def rerank(
        self,
        question: str,
        contexts: list[RetrievedChunk],
    ) -> list[RetrievedChunk]: ...
