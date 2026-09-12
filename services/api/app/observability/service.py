import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import anyio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import RagRun
from app.agents.schemas import AgentResponse
from app.core.exceptions import AppError
from app.documents.models import Document
from app.observability.exporter import TraceExporter
from app.observability.models import AuditEvent
from app.observability.redaction import redact
from app.observability.schemas import AuditEventRead, TraceExportPayload

LOG_LOCK = asyncio.Lock()


class ObservabilityService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        exporter: TraceExporter,
        audit_log_dir: Path,
    ) -> None:
        self.session = session
        self.exporter = exporter
        self.audit_log_dir = audit_log_dir

    async def record_rag_run(self, run: RagRun, response: AgentResponse) -> str:
        raw_payload: dict[str, object] = {
            "question": run.question,
            "answer": run.answer,
            "status": run.status,
            "citation_support_score": run.citation_support_score,
            "retrieved_chunk_count": len(run.retrieved_chunk_ids),
            "steps": [step.model_dump(mode="json") for step in response.steps],
        }
        safe_payload = redact(raw_payload)
        assert isinstance(safe_payload, dict)
        export_payload = TraceExportPayload(
            trace_id=run.trace_id,
            name="agentic-rag-run",
            input={"question": safe_payload["question"]},
            output={
                "answer": safe_payload["answer"],
                "status": run.status,
            },
            metadata={
                "document_id": str(run.document_id),
                "rag_run_id": str(run.id),
                "latency_ms": run.latency_ms,
                "citation_support_score": run.citation_support_score,
                "steps": safe_payload["steps"],
                "token_count": None,
            },
        )
        export_status = await self.exporter.export(export_payload)
        event = AuditEvent(
            trace_id=run.trace_id,
            document_id=run.document_id,
            rag_run_id=run.id,
            event_name="agent.rag.completed",
            level="INFO" if run.status == "answered" else "WARNING",
            duration_ms=run.latency_ms,
            token_count=None,
            payload=safe_payload,
            export_status=export_status,
        )
        self.session.add(event)
        run.observability_status = export_status
        await self.session.commit()
        await self._append_json_log(event)
        return export_status

    async def events(self, document_id: uuid.UUID) -> list[AuditEventRead]:
        if await self.session.scalar(select(Document.id).where(Document.id == document_id)) is None:
            raise AppError(
                code="DOCUMENT_NOT_FOUND",
                message="Dokumen tidak ditemukan",
                status_code=404,
            )
        rows = list(
            (
                await self.session.scalars(
                    select(AuditEvent)
                    .where(AuditEvent.document_id == document_id)
                    .order_by(AuditEvent.created_at.desc())
                )
            ).all()
        )
        return [AuditEventRead.model_validate(row) for row in rows]

    async def _append_json_log(self, event: AuditEvent) -> None:
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)
        path = self.audit_log_dir / f"audit-{datetime.now(UTC):%Y-%m-%d}.jsonl"
        record = {
            "id": str(event.id),
            "trace_id": event.trace_id,
            "document_id": str(event.document_id),
            "rag_run_id": str(event.rag_run_id),
            "event_name": event.event_name,
            "level": event.level,
            "duration_ms": event.duration_ms,
            "token_count": event.token_count,
            "payload": event.payload,
            "export_status": event.export_status,
            "created_at": event.created_at.isoformat(),
        }
        async with LOG_LOCK:
            async with await anyio.open_file(path, "a", encoding="utf-8") as log_file:
                await log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
