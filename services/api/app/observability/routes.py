import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.observability.exporter import TraceExporter, get_trace_exporter
from app.observability.schemas import AuditEventRead
from app.observability.service import ObservabilityService

router = APIRouter(prefix="/documents", tags=["observability"])


def get_observability_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    exporter: Annotated[TraceExporter, Depends(get_trace_exporter)],
) -> ObservabilityService:
    return ObservabilityService(
        session=session,
        exporter=exporter,
        audit_log_dir=settings.audit_log_dir,
    )


@router.get("/{document_id}/trace-events", response_model=list[AuditEventRead])
async def get_trace_events(
    document_id: uuid.UUID,
    service: Annotated[ObservabilityService, Depends(get_observability_service)],
) -> list[AuditEventRead]:
    return await service.events(document_id)
