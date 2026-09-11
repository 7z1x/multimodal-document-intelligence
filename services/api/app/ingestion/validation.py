import hashlib
from dataclasses import dataclass
from pathlib import Path

import anyio
from anyio import to_thread
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import AppError
from app.storage.local import LocalFileStorage

CHUNK_SIZE = 1024 * 1024
ALLOWED_EXTENSIONS = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}
SUFFIX_BY_MEDIA_TYPE = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@dataclass(frozen=True)
class ValidatedUpload:
    temporary_path: Path
    original_filename: str
    media_type: str
    suffix: str
    size_bytes: int
    page_count: int
    sha256: str


def detect_media_type(header: bytes) -> str | None:
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


class UploadValidator:
    def __init__(
        self,
        *,
        storage: LocalFileStorage,
        max_bytes: int,
        max_pages: int,
        max_image_pixels: int = 40_000_000,
    ) -> None:
        self.storage = storage
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self.max_image_pixels = max_image_pixels

    async def validate(self, upload: UploadFile) -> ValidatedUpload:
        await self.storage.prepare()
        temporary_path = self.storage.quarantine_path()
        size_bytes = 0
        digest = hashlib.sha256()
        header = b""

        try:
            async with await anyio.open_file(temporary_path, "wb") as destination:
                while chunk := await upload.read(CHUNK_SIZE):
                    size_bytes += len(chunk)
                    if size_bytes > self.max_bytes:
                        raise AppError(
                            code="FILE_TOO_LARGE",
                            message=f"Ukuran dokumen melebihi batas {self.max_bytes} byte",
                            status_code=413,
                        )
                    if len(header) < 16:
                        header = (header + chunk)[:16]
                    digest.update(chunk)
                    await destination.write(chunk)

            if size_bytes == 0:
                raise AppError(code="EMPTY_FILE", message="Berkas yang diunggah kosong")

            media_type = detect_media_type(header)
            if media_type is None:
                raise AppError(
                    code="UNSUPPORTED_FILE_TYPE",
                    message="Berkas harus berupa PDF, JPG, atau PNG yang valid",
                )

            unsafe_filename = (upload.filename or "document").replace("\\", "/")
            original_filename = unsafe_filename.rsplit("/", maxsplit=1)[-1]
            original_suffix = Path(original_filename).suffix.lower()
            if original_suffix not in ALLOWED_EXTENSIONS[media_type]:
                raise AppError(
                    code="FILE_TYPE_MISMATCH",
                    message="Ekstensi berkas tidak sesuai dengan isi berkas",
                )

            page_count = await self._validate_content(temporary_path, media_type)
            if page_count > self.max_pages:
                raise AppError(
                    code="PAGE_LIMIT_EXCEEDED",
                    message=f"Dokumen melebihi batas maksimal {self.max_pages} halaman",
                    status_code=422,
                )

            return ValidatedUpload(
                temporary_path=temporary_path,
                original_filename=original_filename,
                media_type=media_type,
                suffix=SUFFIX_BY_MEDIA_TYPE[media_type],
                size_bytes=size_bytes,
                page_count=page_count,
                sha256=digest.hexdigest(),
            )
        except BaseException:
            await to_thread.run_sync(temporary_path.unlink, True)
            raise
        finally:
            await upload.close()

    async def _validate_content(self, path: Path, media_type: str) -> int:
        if media_type == "application/pdf":
            return await to_thread.run_sync(self._validate_pdf, path)
        await to_thread.run_sync(self._validate_image, path, self.max_image_pixels)
        return 1

    @staticmethod
    def _validate_pdf(path: Path) -> int:
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise AppError(
                    code="ENCRYPTED_PDF",
                    message="PDF yang dilindungi kata sandi belum didukung",
                    status_code=422,
                )
            return len(reader.pages)
        except AppError:
            raise
        except (PdfReadError, OSError, ValueError) as exc:
            raise AppError(code="CORRUPT_PDF", message="PDF rusak atau tidak dapat dibaca") from exc

    @staticmethod
    def _validate_image(path: Path, max_image_pixels: int) -> None:
        try:
            with Image.open(path) as image:
                width, height = image.size
                if width * height > max_image_pixels:
                    raise AppError(
                        code="IMAGE_DIMENSIONS_EXCEEDED",
                        message="Resolusi gambar melebihi batas pemrosesan",
                        status_code=422,
                    )
                image.verify()
        except AppError:
            raise
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise AppError(
                code="CORRUPT_IMAGE",
                message="Gambar rusak atau tidak dapat dibaca",
            ) from exc
