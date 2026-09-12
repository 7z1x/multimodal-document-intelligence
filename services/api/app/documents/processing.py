import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import RagRun
from app.core.exceptions import AppError
from app.documents.models import Document, DocumentStatus
from app.documents.page_models import DocumentPage
from app.extraction.base import InvoiceExtractor
from app.extraction.models import InvoiceExtractionRecord
from app.extraction.schemas import StructuredExtraction
from app.ingestion.parser import DocumentParser
from app.retrieval.models import DocumentChunk
from app.storage.local import LocalFileStorage


class DocumentProcessingService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: LocalFileStorage,
        parser: DocumentParser,
        extractor: InvoiceExtractor,
    ) -> None:
        self.session = session
        self.storage = storage
        self.parser = parser
        self.extractor = extractor

    async def process(self, document_id: uuid.UUID) -> StructuredExtraction:
        document = await self._get_document(document_id)
        document.status = DocumentStatus.PROCESSING
        document.error_code = None
        document.error_message = None
        await self.session.commit()

        try:
            path = self.storage.resolve(document.stored_filename)
            if not path.is_file():
                raise AppError(
                    code="DOCUMENT_FILE_MISSING",
                    message="Berkas dokumen tidak ditemukan di storage",
                    status_code=500,
                )

            pages = await self.parser.parse(path, document.media_type)
            await self.session.execute(
                delete(DocumentPage).where(DocumentPage.document_id == document_id)
            )
            await self.session.execute(
                delete(InvoiceExtractionRecord).where(
                    InvoiceExtractionRecord.document_id == document_id
                )
            )
            await self.session.execute(delete(RagRun).where(RagRun.document_id == document_id))
            await self.session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            self.session.add_all(
                [
                    DocumentPage(
                        document_id=document_id,
                        page_number=page.page_number,
                        extraction_method=page.extraction_method,
                        text=page.text,
                        character_count=page.character_count,
                        ocr_confidence=page.ocr_confidence,
                        layout_json=page.layout,
                    )
                    for page in pages
                ]
            )
            document.status = DocumentStatus.TEXT_EXTRACTED
            await self.session.commit()

            extraction = await self.extractor.extract(pages)
            record = InvoiceExtractionRecord(
                document_id=document_id,
                backend=extraction.backend,
                payload=extraction.data.model_dump(mode="json"),
                evidence={
                    key: [item.model_dump(mode="json") for item in items]
                    for key, items in extraction.evidence.items()
                },
                is_math_valid=extraction.is_math_valid,
                validation_errors=list(extraction.validation_errors),
            )
            self.session.add(record)
            document.status = DocumentStatus.STRUCTURE_EXTRACTED
            await self.session.commit()
            return extraction
        except Exception as exc:
            await self.session.rollback()
            document = await self._get_document(document_id)
            document.status = DocumentStatus.FAILED
            if isinstance(exc, AppError):
                document.error_code = exc.code
                document.error_message = exc.message
            else:
                document.error_code = "DOCUMENT_PROCESSING_FAILED"
                document.error_message = "Dokumen gagal diproses"
            await self.session.commit()
            if isinstance(exc, AppError):
                raise
            raise AppError(
                code="DOCUMENT_PROCESSING_FAILED",
                message="Dokumen gagal diproses",
                status_code=500,
            ) from exc

    async def pages(self, document_id: uuid.UUID) -> list[DocumentPage]:
        await self._get_document(document_id)
        result = await self.session.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        )
        return list(result.scalars())

    async def extraction(self, document_id: uuid.UUID) -> InvoiceExtractionRecord:
        await self._get_document(document_id)
        result = await self.session.execute(
            select(InvoiceExtractionRecord).where(
                InvoiceExtractionRecord.document_id == document_id
            )
        )
        extraction = result.scalar_one_or_none()
        if extraction is None:
            raise AppError(
                code="EXTRACTION_NOT_FOUND",
                message="Hasil ekstraksi invoice belum tersedia",
                status_code=404,
            )
        return extraction

    async def _get_document(self, document_id: uuid.UUID) -> Document:
        result = await self.session.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        return document
