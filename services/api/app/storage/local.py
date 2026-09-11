import os
import uuid
from pathlib import Path

from anyio import to_thread


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.quarantine = self.root / ".quarantine"

    async def prepare(self) -> None:
        await to_thread.run_sync(self.root.mkdir, 0o700, True, True)
        await to_thread.run_sync(self.quarantine.mkdir, 0o700, True, True)

    def quarantine_path(self) -> Path:
        return self.quarantine / f"{uuid.uuid4()}.upload"

    async def commit(self, temporary_path: Path, document_id: uuid.UUID, suffix: str) -> str:
        filename = f"{document_id}{suffix}"
        destination = (self.root / filename).resolve()
        if destination.parent != self.root:
            raise ValueError("Resolved storage path escaped the storage directory")
        await to_thread.run_sync(os.replace, temporary_path, destination)
        return filename

    async def delete(self, filename: str) -> None:
        target = self.resolve(filename)
        await to_thread.run_sync(target.unlink, True)

    def resolve(self, filename: str) -> Path:
        target = (self.root / filename).resolve()
        if target.parent != self.root:
            raise ValueError("Resolved storage path escaped the storage directory")
        return target
