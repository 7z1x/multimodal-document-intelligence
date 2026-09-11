import uuid
from pathlib import Path

from anyio import to_thread
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.documents.models import Document
from app.ingestion.validation import UploadValidator
from app.storage.local import LocalFileStorage


class DocumentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: LocalFileStorage,
        validator: UploadValidator,
    ) -> None:
        self.session = session
        self.storage = storage
        self.validator = validator

    async def create(self, upload: UploadFile) -> Document:
        validated = await self.validator.validate(upload)
        document_id = uuid.uuid4()
        stored_filename: str | None = None

        try:
            stored_filename = await self.storage.commit(
                validated.temporary_path,
                document_id,
                validated.suffix,
            )
            document = Document(
                id=document_id,
                original_filename=validated.original_filename,
                stored_filename=stored_filename,
                media_type=validated.media_type,
                size_bytes=validated.size_bytes,
                page_count=validated.page_count,
                sha256=validated.sha256,
            )
            self.session.add(document)
            await self.session.commit()
            await self.session.refresh(document)
            return document
        except Exception as exc:
            await self.session.rollback()
            if stored_filename is not None:
                await self.storage.delete(stored_filename)
            else:
                await to_thread.run_sync(Path(validated.temporary_path).unlink, True)
            if isinstance(exc, SQLAlchemyError):
                raise AppError(
                    code="DOCUMENT_PERSISTENCE_FAILED",
                    message="Metadata dokumen gagal disimpan",
                    status_code=500,
                ) from exc
            raise

    async def get(self, document_id: uuid.UUID) -> Document:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        return document
