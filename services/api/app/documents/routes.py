import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.db.session import get_db_session
from app.documents.processing import DocumentProcessingService
from app.documents.schemas import (
    DocumentPageRead,
    DocumentRead,
    DocumentStatusRead,
    InvoiceExtractionRead,
)
from app.documents.service import DocumentService
from app.extraction.base import InvoiceExtractor
from app.extraction.heuristic import HeuristicInvoiceExtractor
from app.extraction.opencode import OpenCodeInvoiceExtractor
from app.extraction.schemas import FieldEvidence, InvoiceData
from app.ingestion.parser import DocumentParser
from app.ingestion.validation import UploadValidator
from app.ocr.paddle import LazyPaddleStructureEngine
from app.providers.opencode import OpenCodeStructuredClient
from app.storage.local import LocalFileStorage

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    storage = LocalFileStorage(settings.storage_dir)
    validator = UploadValidator(
        storage=storage,
        max_bytes=settings.max_upload_bytes,
        max_pages=settings.max_document_pages,
        max_image_pixels=settings.max_image_pixels,
    )
    return DocumentService(session=session, storage=storage, validator=validator)


def get_processing_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentProcessingService:
    storage = LocalFileStorage(settings.storage_dir)
    parser = DocumentParser(
        ocr_engine=LazyPaddleStructureEngine(),
        native_min_characters=settings.native_text_min_characters,
    )
    extractor: InvoiceExtractor
    if settings.extraction_backend == "heuristic":
        extractor = HeuristicInvoiceExtractor()
    elif settings.extraction_backend == "opencode":
        extractor = OpenCodeInvoiceExtractor(
            client=OpenCodeStructuredClient(
                base_url=settings.opencode_base_url,
                provider=settings.opencode_provider,
                model=settings.opencode_model,
                directory=settings.opencode_directory,
                timeout_seconds=settings.opencode_timeout_seconds,
            ),
            max_characters=settings.max_extraction_characters,
        )
    else:
        raise AppError(
            code="INVALID_EXTRACTION_BACKEND",
            message="EXTRACTION_BACKEND harus bernilai 'heuristic' atau 'opencode'",
            status_code=500,
        )
    return DocumentProcessingService(
        session=session,
        storage=storage,
        parser=parser,
        extractor=extractor,
    )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="Invoice PDF, JPG, or PNG")],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return DocumentRead.model_validate(await service.create(file))


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentRead:
    return DocumentRead.model_validate(await service.get(document_id))


@router.get("/{document_id}/status", response_model=DocumentStatusRead)
async def get_document_status(
    document_id: uuid.UUID,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentStatusRead:
    document = await service.get(document_id)
    return DocumentStatusRead(
        id=document.id,
        status=document.status,
        error_code=document.error_code,
        error_message=document.error_message,
    )


@router.post("/{document_id}/process", response_model=InvoiceExtractionRead)
async def process_document(
    document_id: uuid.UUID,
    service: Annotated[DocumentProcessingService, Depends(get_processing_service)],
) -> InvoiceExtractionRead:
    result = await service.process(document_id)
    return InvoiceExtractionRead(**result.model_dump())


@router.get("/{document_id}/pages", response_model=list[DocumentPageRead])
async def get_document_pages(
    document_id: uuid.UUID,
    service: Annotated[DocumentProcessingService, Depends(get_processing_service)],
) -> list[DocumentPageRead]:
    return [DocumentPageRead.model_validate(page) for page in await service.pages(document_id)]


@router.get("/{document_id}/extraction", response_model=InvoiceExtractionRead)
async def get_invoice_extraction(
    document_id: uuid.UUID,
    service: Annotated[DocumentProcessingService, Depends(get_processing_service)],
) -> InvoiceExtractionRead:
    record = await service.extraction(document_id)
    return InvoiceExtractionRead(
        data=InvoiceData.model_validate(record.payload),
        evidence={
            key: [FieldEvidence.model_validate(item) for item in items]
            for key, items in record.evidence.items()
        },
        backend=record.backend,
        is_math_valid=record.is_math_valid,
        validation_errors=[str(item) for item in record.validation_errors],
    )
