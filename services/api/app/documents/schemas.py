import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.documents.models import DocumentStatus
from app.extraction.schemas import FieldEvidence, InvoiceData


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    media_type: str
    size_bytes: int
    page_count: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class DocumentStatusRead(BaseModel):
    id: uuid.UUID
    status: DocumentStatus
    error_code: str | None = None
    error_message: str | None = None


class DocumentPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    extraction_method: str
    text: str
    character_count: int
    ocr_confidence: float | None
    layout_json: dict[str, object]


class InvoiceExtractionRead(BaseModel):
    data: InvoiceData
    evidence: dict[str, list[FieldEvidence]]
    backend: str
    is_math_valid: bool | None
    validation_errors: list[str]
