import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trace_id: str
    document_id: uuid.UUID
    rag_run_id: uuid.UUID
    event_name: str
    level: str
    duration_ms: int
    token_count: int | None
    payload: dict[str, object]
    export_status: str
    created_at: datetime


class TraceExportPayload(BaseModel):
    trace_id: str
    name: str
    input: dict[str, object]
    output: dict[str, object]
    metadata: dict[str, object]
