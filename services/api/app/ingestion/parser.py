from dataclasses import dataclass, field
from pathlib import Path

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from anyio import to_thread
from PIL import Image
from pypdf import PdfReader

from app.core.exceptions import AppError
from app.ocr.base import OcrEngine


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    extraction_method: str
    text: str
    character_count: int
    ocr_confidence: float | None = None
    layout: dict[str, object] = field(default_factory=dict)


class DocumentParser:
    def __init__(self, *, ocr_engine: OcrEngine | None, native_min_characters: int = 40) -> None:
        self.ocr_engine = ocr_engine
        self.native_min_characters = native_min_characters

    async def parse(self, path: Path, media_type: str) -> list[ParsedPage]:
        return await to_thread.run_sync(self._parse_sync, path, media_type)

    def _parse_sync(self, path: Path, media_type: str) -> list[ParsedPage]:
        if media_type == "application/pdf":
            return self._parse_pdf(path)
        if media_type in {"image/jpeg", "image/png"}:
            with Image.open(path) as source:
                image = source.convert("RGB")
            return [self._ocr_page(image, page_number=1)]
        raise AppError(code="UNSUPPORTED_FILE_TYPE", message="Tipe dokumen tidak didukung")

    def _parse_pdf(self, path: Path) -> list[ParsedPage]:
        reader = PdfReader(path)
        native_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        parsed_pages: list[ParsedPage] = []
        pdf_document: pdfium.PdfDocument | None = None

        try:
            for index, native_text in enumerate(native_texts):
                page_number = index + 1
                character_count = len("".join(native_text.split()))
                if character_count >= self.native_min_characters:
                    parsed_pages.append(
                        ParsedPage(
                            page_number=page_number,
                            extraction_method="native",
                            text=native_text,
                            character_count=character_count,
                        )
                    )
                    continue

                if self.ocr_engine is None:
                    raise AppError(
                        code="OCR_REQUIRED",
                        message=(
                            f"Halaman {page_number} memerlukan OCR tetapi engine belum tersedia"
                        ),
                        status_code=503,
                    )
                if pdf_document is None:
                    pdf_document = pdfium.PdfDocument(path)
                pdf_page = pdf_document[index]
                bitmap = pdf_page.render(scale=300 / 72)
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
                    pdf_page.close()
                parsed_pages.append(self._ocr_page(image, page_number=page_number))
        finally:
            if pdf_document is not None:
                pdf_document.close()

        return parsed_pages

    def _ocr_page(self, image: Image.Image, *, page_number: int) -> ParsedPage:
        if self.ocr_engine is None:
            raise AppError(
                code="OCR_REQUIRED",
                message=f"Halaman {page_number} memerlukan OCR tetapi engine belum tersedia",
                status_code=503,
            )
        result = self.ocr_engine.recognize(image)
        blocks = [
            {
                "text": block.text,
                "confidence": block.confidence,
                "polygon": block.polygon,
            }
            for block in result.blocks
        ]
        return ParsedPage(
            page_number=page_number,
            extraction_method="ocr",
            text=result.text,
            character_count=len("".join(result.text.split())),
            ocr_confidence=result.confidence,
            layout={"blocks": blocks, **result.layout},
        )
