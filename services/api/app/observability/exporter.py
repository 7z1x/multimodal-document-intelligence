from functools import lru_cache
from typing import Protocol

import anyio
from langfuse import Langfuse

from app.core.config import get_settings
from app.observability.schemas import TraceExportPayload


class TraceExporter(Protocol):
    async def export(self, payload: TraceExportPayload) -> str: ...


class DisabledTraceExporter:
    def __init__(self, status: str = "disabled") -> None:
        self.status = status

    async def export(self, payload: TraceExportPayload) -> str:
        del payload
        return self.status


class LangfuseTraceExporter:
    def __init__(self, client: Langfuse) -> None:
        self.client = client

    async def export(self, payload: TraceExportPayload) -> str:
        try:
            await anyio.to_thread.run_sync(self._export_sync, payload)
        except Exception:  # exporter must never break the document workflow
            return "failed"
        return "sent"

    def _export_sync(self, payload: TraceExportPayload) -> None:
        with self.client.start_as_current_observation(
            trace_context={"trace_id": payload.trace_id},
            name=payload.name,
            as_type="agent",
            input=payload.input,
            metadata=payload.metadata,
        ) as observation:
            observation.update(output=payload.output)
        self.client.flush()


@lru_cache
def get_trace_exporter() -> TraceExporter:
    settings = get_settings()
    if not settings.langfuse_enabled:
        return DisabledTraceExporter()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return DisabledTraceExporter("misconfigured")
    return LangfuseTraceExporter(
        Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            base_url=settings.langfuse_base_url,
            environment=settings.app_env,
            timeout=settings.langfuse_timeout_seconds,
        )
    )
