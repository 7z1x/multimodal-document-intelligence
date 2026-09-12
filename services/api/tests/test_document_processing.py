from io import BytesIO
from typing import cast

import pytest
from fastapi import UploadFile
from PIL import Image
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import DocumentStatus
from app.documents.processing import DocumentProcessingService
from app.documents.service import DocumentService
from app.extraction.heuristic import HeuristicInvoiceExtractor, parse_amount
from app.extraction.opencode import OpenCodeInvoiceExtractor
from app.extraction.schemas import InvoiceData
from app.ingestion.parser import DocumentParser, ParsedPage
from app.ingestion.validation import UploadValidator
from app.ocr.schemas import OcrBlock, OcrPageResult
from app.providers.opencode import OpenCodeStructuredClient
from app.storage.local import LocalFileStorage


def invoice_pdf_bytes() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    lines = [
        "INVOICE",
        "Invoice Number: INV-2026-001",
        "Invoice Date: 12/09/2026",
        "Due Date: 19/09/2026",
        "Vendor: PT Contoh Nusantara",
        "Buyer: Toko Belajar AI",
        "Subtotal: Rp 100.000,00",
        "PPN: Rp 10.000,00",
        "Grand Total: Rp 110.000,00",
    ]
    y = 800
    for line in lines:
        pdf.drawString(60, y, line)
        y -= 28
    pdf.save()
    return output.getvalue()


class FakeOcrEngine:
    def recognize(self, _: Image.Image) -> OcrPageResult:
        return OcrPageResult(
            text="Invoice Number: SCAN-001",
            confidence=0.94,
            blocks=[OcrBlock(text="Invoice Number: SCAN-001", confidence=0.94)],
            layout={"tables": []},
        )


@pytest.mark.asyncio
async def test_native_pdf_text_is_preserved(tmp_path) -> None:
    path = tmp_path / "invoice.pdf"
    path.write_bytes(invoice_pdf_bytes())
    parser = DocumentParser(ocr_engine=None, native_min_characters=40)

    pages = await parser.parse(path, "application/pdf")

    assert len(pages) == 1
    assert pages[0].extraction_method == "native"
    assert "INV-2026-001" in pages[0].text


@pytest.mark.asyncio
async def test_image_uses_ocr_and_keeps_confidence(tmp_path) -> None:
    path = tmp_path / "scan.png"
    Image.new("RGB", (80, 40), "white").save(path)
    parser = DocumentParser(ocr_engine=FakeOcrEngine())

    pages = await parser.parse(path, "image/png")

    assert pages[0].extraction_method == "ocr"
    assert pages[0].ocr_confidence == pytest.approx(0.94)
    assert pages[0].layout["blocks"][0]["text"] == "Invoice Number: SCAN-001"


@pytest.mark.asyncio
async def test_heuristic_extraction_is_transparent_and_math_checked() -> None:
    page = ParsedPage(
        page_number=1,
        extraction_method="native",
        text="\n".join(
            [
                "Invoice Number: INV-2026-001",
                "Invoice Date: 12/09/2026",
                "Due Date: 19/09/2026",
                "Vendor: PT Contoh Nusantara",
                "Buyer: Toko Belajar AI",
                "Subtotal: Rp 100.000,00",
                "PPN: Rp 10.000,00",
                "Grand Total: Rp 110.000,00",
            ]
        ),
        character_count=100,
    )

    result = await HeuristicInvoiceExtractor().extract([page])

    assert result.data.invoice_number == "INV-2026-001"
    assert result.data.currency == "IDR"
    assert result.data.total_amount == parse_amount("110.000,00")
    assert result.is_math_valid is True
    assert result.evidence["invoice_number"][0].page_number == 1
    assert result.evidence["total_amount"][0].snippet == "Grand Total: Rp 110.000,00"


@pytest.mark.asyncio
async def test_processing_service_persists_pages_and_extraction(
    tmp_path,
    session: AsyncSession,
) -> None:
    storage = LocalFileStorage(tmp_path / "documents")
    validator = UploadValidator(storage=storage, max_bytes=1_000_000, max_pages=10)
    document_service = DocumentService(session=session, storage=storage, validator=validator)
    upload = UploadFile(file=BytesIO(invoice_pdf_bytes()), filename="invoice.pdf")
    document = await document_service.create(upload)
    processing = DocumentProcessingService(
        session=session,
        storage=storage,
        parser=DocumentParser(ocr_engine=None, native_min_characters=40),
        extractor=HeuristicInvoiceExtractor(),
    )

    extraction = await processing.process(document.id)
    pages = await processing.pages(document.id)
    record = await processing.extraction(document.id)

    assert document.status == DocumentStatus.STRUCTURE_EXTRACTED
    assert len(pages) == 1
    assert extraction.data.invoice_number == "INV-2026-001"
    assert record.backend == "heuristic"
    assert record.is_math_valid is True


@pytest.mark.asyncio
async def test_opencode_extractor_validates_response() -> None:
    class FakeOpenCodeClient:
        async def generate(self, schema: type[InvoiceData], **_: object) -> InvoiceData:
            return schema.model_validate(
                {
                    "invoice_number": "INV-MUSE-001",
                    "invoice_date": "2026-09-12",
                    "currency": "IDR",
                    "vendor_name": "PT Model Online",
                    "line_items": [],
                    "subtotal": "100000",
                    "tax_amount": "11000",
                    "total_amount": "111000",
                }
            )

    extractor = OpenCodeInvoiceExtractor(
        client=cast(OpenCodeStructuredClient, FakeOpenCodeClient()),
        max_characters=30_000,
    )
    page = ParsedPage(
        page_number=1,
        extraction_method="native",
        text="Invoice Number: INV-MUSE-001\nTotal: IDR 111000",
        character_count=49,
    )

    result = await extractor.extract([page])

    assert result.backend == "opencode"
    assert result.data.invoice_number == "INV-MUSE-001"
    assert result.is_math_valid is True
