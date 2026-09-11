from collections.abc import AsyncIterator
from io import BytesIO

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pypdf import PdfWriter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.db.base import Base
from app.db.session import get_db_session
from app.documents.service import DocumentService
from app.ingestion.validation import UploadValidator
from app.main import app
from app.storage.local import LocalFileStorage


def pdf_bytes(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def png_bytes(width: int = 4, height: int = 4) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color="white").save(output, format="PNG")
    return output.getvalue()


def invoice_pdf_bytes() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    for index, line in enumerate(
        [
            "Invoice Number: API-2026-001",
            "Invoice Date: 12/09/2026",
            "Vendor: PT Endpoint Test",
            "Subtotal: Rp 100.000,00",
            "PPN: Rp 10.000,00",
            "Grand Total: Rp 110.000,00",
        ]
    ):
        pdf.drawString(60, 800 - index * 28, line)
    pdf.save()
    return output.getvalue()


@pytest.mark.asyncio
async def test_valid_pdf_is_stored_with_generated_name(tmp_path, session: AsyncSession) -> None:
    storage = LocalFileStorage(tmp_path / "documents")
    validator = UploadValidator(storage=storage, max_bytes=1_000_000, max_pages=10)
    service = DocumentService(session=session, storage=storage, validator=validator)
    upload = UploadFile(file=BytesIO(pdf_bytes(2)), filename="../../private-invoice.pdf")

    document = await service.create(upload)

    assert document.original_filename == "private-invoice.pdf"
    assert document.page_count == 2
    assert document.media_type == "application/pdf"
    assert document.stored_filename != document.original_filename
    assert (storage.root / document.stored_filename).is_file()
    assert not any(storage.quarantine.iterdir())


@pytest.mark.asyncio
async def test_executable_renamed_as_pdf_is_rejected(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "documents")
    validator = UploadValidator(storage=storage, max_bytes=1_000_000, max_pages=10)
    upload = UploadFile(file=BytesIO(b"MZ" + b"\x00" * 100), filename="malware.pdf")

    with pytest.raises(AppError) as error:
        await validator.validate(upload)

    assert error.value.code == "UNSUPPORTED_FILE_TYPE"
    assert not any(storage.quarantine.iterdir())


@pytest.mark.asyncio
async def test_pdf_above_page_limit_is_rejected(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "documents")
    validator = UploadValidator(storage=storage, max_bytes=1_000_000, max_pages=10)
    upload = UploadFile(file=BytesIO(pdf_bytes(11)), filename="eleven-pages.pdf")

    with pytest.raises(AppError) as error:
        await validator.validate(upload)

    assert error.value.code == "PAGE_LIMIT_EXCEEDED"
    assert error.value.status_code == 422
    assert not any(storage.quarantine.iterdir())


@pytest.mark.asyncio
async def test_image_dimensions_are_limited(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "documents")
    validator = UploadValidator(
        storage=storage,
        max_bytes=1_000_000,
        max_pages=10,
        max_image_pixels=10,
    )
    upload = UploadFile(file=BytesIO(png_bytes(4, 4)), filename="large-dimensions.png")

    with pytest.raises(AppError) as error:
        await validator.validate(upload)

    assert error.value.code == "IMAGE_DIMENSIONS_EXCEEDED"
    assert not any(storage.quarantine.iterdir())


@pytest.mark.asyncio
async def test_upload_endpoint_returns_public_document_metadata(tmp_path) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as db_session:
            yield db_session

    def override_settings() -> Settings:
        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            storage_dir=tmp_path / "documents",
        )

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = override_settings
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/documents",
                files={"file": ("invoice.pdf", pdf_bytes(1), "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "invoice.pdf"
    assert payload["page_count"] == 1
    assert payload["status"] == "stored"
    assert "stored_filename" not in payload


@pytest.mark.asyncio
async def test_processing_endpoints_return_pages_and_structured_invoice(tmp_path) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as db_session:
            yield db_session

    def override_settings() -> Settings:
        return Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            storage_dir=tmp_path / "documents",
            extraction_backend="heuristic",
        )

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_settings] = override_settings
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            upload_response = await client.post(
                "/api/v1/documents",
                files={"file": ("invoice.pdf", invoice_pdf_bytes(), "application/pdf")},
            )
            document_id = upload_response.json()["id"]
            process_response = await client.post(f"/api/v1/documents/{document_id}/process")
            pages_response = await client.get(f"/api/v1/documents/{document_id}/pages")
            extraction_response = await client.get(f"/api/v1/documents/{document_id}/extraction")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()

    assert upload_response.status_code == 201
    assert process_response.status_code == 200
    assert process_response.json()["data"]["invoice_number"] == "API-2026-001"
    assert process_response.json()["is_math_valid"] is True
    assert pages_response.status_code == 200
    assert pages_response.json()[0]["extraction_method"] == "native"
    assert extraction_response.status_code == 200
    assert extraction_response.json()["backend"] == "heuristic"
