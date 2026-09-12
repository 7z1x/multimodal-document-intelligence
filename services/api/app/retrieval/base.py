import uuid
from typing import Protocol

from app.retrieval.schemas import ChunkDraft, RetrievedChunk


class ChunkRepository(Protocol):
    async def replace(
        self,
        document_id: uuid.UUID,
        chunks: list[ChunkDraft],
    ) -> None: ...

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]: ...


class Retriever(Protocol):
    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]: ...
