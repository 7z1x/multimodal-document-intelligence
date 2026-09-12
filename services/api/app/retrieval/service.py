import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.documents.models import Document, DocumentStatus
from app.documents.page_models import DocumentPage
from app.retrieval.base import ChunkRepository, Retriever
from app.retrieval.chunking import PageAwareChunker
from app.retrieval.schemas import IndexResult, RetrievedChunk


class DocumentIndexingService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        chunker: PageAwareChunker,
        repository: ChunkRepository,
    ) -> None:
        self.session = session
        self.chunker = chunker
        self.repository = repository

    async def index(self, document_id: uuid.UUID) -> IndexResult:
        document = await self._get_document(document_id)
        if document.status not in {DocumentStatus.STRUCTURE_EXTRACTED, DocumentStatus.INDEXED}:
            raise AppError(
                code="DOCUMENT_NOT_READY_FOR_INDEXING",
                message="Dokumen harus selesai diekstrak sebelum dibuatkan indeks RAG",
                status_code=409,
            )
        document.status = DocumentStatus.INDEXING
        document.error_code = None
        document.error_message = None
        await self.session.commit()

        try:
            pages = list(
                (
                    await self.session.scalars(
                        select(DocumentPage)
                        .where(DocumentPage.document_id == document_id)
                        .order_by(DocumentPage.page_number)
                    )
                ).all()
            )
            chunks = self.chunker.split(pages)
            if not chunks:
                raise AppError(
                    code="DOCUMENT_HAS_NO_INDEXABLE_TEXT",
                    message="Dokumen tidak memiliki teks yang dapat dibuatkan indeks",
                    status_code=422,
                )
            await self.repository.replace(document_id, chunks)
            document.status = DocumentStatus.INDEXED
            await self.session.commit()
            return IndexResult(
                document_id=document_id,
                chunk_count=len(chunks),
                retrieval_method="postgresql-full-text",
            )
        except Exception as exc:
            await self.session.rollback()
            document = await self._get_document(document_id)
            document.status = DocumentStatus.STRUCTURE_EXTRACTED
            if isinstance(exc, AppError):
                document.error_code = exc.code
                document.error_message = exc.message
            else:
                document.error_code = "DOCUMENT_INDEXING_FAILED"
                document.error_message = "Indeks RAG gagal dibuat"
            await self.session.commit()
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="DOCUMENT_INDEXING_FAILED",
                message="Indeks RAG gagal dibuat",
                status_code=500,
            ) from exc

    async def _get_document(self, document_id: uuid.UUID) -> Document:
        document = await self.session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        return document


class TextRetriever:
    def __init__(self, *, repository: ChunkRepository) -> None:
        self.repository = repository

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        return await self.repository.search(document_id, query, limit)


class DocumentSearchService:
    def __init__(self, *, session: AsyncSession, retriever: Retriever) -> None:
        self.session = session
        self.retriever = retriever

    async def search(
        self,
        document_id: uuid.UUID,
        query: str,
        limit: int,
    ) -> list[RetrievedChunk]:
        document = await self.session.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        if document.status != DocumentStatus.INDEXED:
            raise AppError(
                code="DOCUMENT_NOT_INDEXED",
                message="Buat indeks RAG dokumen sebelum melakukan pencarian",
                status_code=409,
            )
        return await self.retriever.search(document_id, query, limit)
