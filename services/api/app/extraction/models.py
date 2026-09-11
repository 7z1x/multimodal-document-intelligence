import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvoiceExtractionRecord(Base):
    __tablename__ = "invoice_extractions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    backend: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    evidence: Mapped[dict[str, list[dict[str, object]]]] = mapped_column(JSON, default=dict)
    is_math_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
