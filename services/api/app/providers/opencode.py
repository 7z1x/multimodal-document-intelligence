import json
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.exceptions import AppError

SchemaT = TypeVar("SchemaT", bound=BaseModel)

DISABLED_TOOLS = (
    "question",
    "bash",
    "read",
    "glob",
    "grep",
    "edit",
    "write",
    "task",
    "webfetch",
    "todowrite",
    "websearch",
    "skill",
    "apply_patch",
)


class OpenCodeStructuredClient:
    """Restricted OpenCode client for online model inference.

    Every request gets an isolated session with all coding tools denied. This keeps
    untrusted document content from reading or changing files on the host machine.
    """

    def __init__(
        self,
        *,
        base_url: str,
        provider: str,
        model: str,
        directory: Path,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.model = model
        self.directory = directory
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def generate(
        self,
        schema: type[SchemaT],
        *,
        system: str,
        prompt: str,
        title: str,
    ) -> SchemaT:
        session_id: str | None = None
        params = {"directory": str(self.directory)}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                session_response = await client.post(
                    "/session",
                    params=params,
                    json={
                        "title": title,
                        "model": {"providerID": self.provider, "id": self.model},
                        "permission": [
                            {"permission": "*", "pattern": "*", "action": "deny"}
                        ],
                    },
                )
                session_response.raise_for_status()
                session_id = str(session_response.json()["id"])

                json_schema = json.dumps(schema.model_json_schema(), separators=(",", ":"))
                response = await client.post(
                    f"/session/{session_id}/message",
                    params=params,
                    json={
                        "model": {
                            "providerID": self.provider,
                            "modelID": self.model,
                        },
                        "tools": {tool: False for tool in DISABLED_TOOLS},
                        "system": (
                            f"{system}\nAll tools are disabled. Return only valid JSON matching "
                            f"this schema: {json_schema}"
                        ),
                        "parts": [{"type": "text", "text": prompt}],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("info", {}).get("error"):
                    raise ValueError("OpenCode returned a provider error")
                if any(part.get("type") == "tool" for part in payload.get("parts", [])):
                    raise ValueError("OpenCode attempted to use a disabled tool")
                content = "".join(
                    str(part.get("text", ""))
                    for part in payload.get("parts", [])
                    if part.get("type") == "text"
                ).strip()
                return schema.model_validate_json(self._strip_json_fence(content))
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise AppError(
                code="OPENCODE_MODEL_FAILED",
                message=(
                    "OpenCode/Muse Spark gagal menghasilkan respons terstruktur. "
                    "Pastikan `opencode serve` aktif dan akun OpenCode terhubung."
                ),
                status_code=502,
            ) from exc
        finally:
            if session_id is not None:
                try:
                    async with httpx.AsyncClient(
                        base_url=self.base_url,
                        timeout=10,
                        transport=self.transport,
                    ) as cleanup_client:
                        await cleanup_client.delete(
                            f"/session/{session_id}",
                            params=params,
                        )
                except httpx.HTTPError:
                    pass

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        if not content.startswith("```"):
            return content
        lines = content.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return content
