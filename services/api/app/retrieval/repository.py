import re
import uuid
from typing import Literal, cast

from sqlalchemy import delete, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.retrieval.models import DocumentChunk
from app.retrieval.schemas import ChunkDraft, RetrievedChunk


class PostgresTextChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace(
        self,
        document_id: uuid.UUID,
        chunks: list[ChunkDraft],
    ) -> None:
        await self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        self.session.add_all(
            [
                DocumentChunk(
                    document_id=document_id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    chunk_type=chunk.chunk_type,
                    content=chunk.content,
                    token_count=chunk.token_count,
                )
                for chunk in chunks
            ]
        )

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            results = await self._postgres_search(document_id, query, limit)
            if results:
                return results
        return await self._portable_search(document_id, query, limit)

    async def _postgres_search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        text_search_config: ColumnElement[str] = literal_column("'simple'")
        search_vector = func.to_tsvector(text_search_config, DocumentChunk.content)
        search_query = func.plainto_tsquery(text_search_config, query)
        rank = func.ts_rank_cd(search_vector, search_query)
        statement = (
            select(DocumentChunk, rank.label("rank"))
            .where(
                DocumentChunk.document_id == document_id,
                search_vector.op("@@")(search_query),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [self._result(chunk, min(1.0, float(raw_rank) * 5)) for chunk, raw_rank in rows]

    async def _portable_search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        chunks = list(
            (
                await self.session.scalars(
                    select(DocumentChunk).where(DocumentChunk.document_id == document_id)
                )
            ).all()
        )
        terms = {term for term in re.findall(r"[\w.-]+", query.casefold()) if len(term) > 1}
        if not terms:
            return []
        scored: list[tuple[DocumentChunk, float]] = []
        for chunk in chunks:
            content = chunk.content.casefold()
            matched = sum(1 for term in terms if term in content)
            if matched:
                scored.append((chunk, matched / len(terms)))
        scored.sort(key=lambda item: (-item[1], item[0].chunk_index))
        return [self._result(chunk, score) for chunk, score in scored[:limit]]

    @staticmethod
    def _result(chunk: DocumentChunk, score: float) -> RetrievedChunk:
        return RetrievedChunk(
            id=chunk.id,
            document_id=chunk.document_id,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            chunk_type=cast(Literal["text", "table"], chunk.chunk_type),
            content=chunk.content,
            relevance_score=max(0.0, min(1.0, score)),
        )

    async def count(self, document_id: uuid.UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return int(result or 0)
