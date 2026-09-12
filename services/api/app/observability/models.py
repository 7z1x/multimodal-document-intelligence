import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[str] = mapped_column(String(32), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    rag_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("rag_runs.id", ondelete="CASCADE"),
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(96))
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    duration_ms: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    export_status: Mapped[str] = mapped_column(String(24), default="disabled")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
