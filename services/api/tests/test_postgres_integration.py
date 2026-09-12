import os
import uuid

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.documents.models import Document, DocumentStatus
from app.retrieval.repository import PostgresTextChunkRepository
from app.retrieval.schemas import ChunkDraft


def _document(label: str) -> Document:
    identifier = uuid.uuid4()
    return Document(
        id=identifier,
        original_filename=f"{label}.pdf",
        stored_filename=f"integration-{identifier}.pdf",
        media_type="application/pdf",
        size_bytes=100,
        page_count=1,
        sha256=identifier.hex.ljust(64, "0"),
        status=DocumentStatus.INDEXED,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_migrations_and_document_scoped_full_text_search() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    first = _document("first")
    second = _document("second")
    try:
        async with factory() as session:
            assert session.bind is not None
            assert session.bind.dialect.name == "postgresql"
            migration = await session.scalar(text("SELECT version_num FROM alembic_version"))
            assert migration == "20260912_0005"

            session.add_all([first, second])
            await session.flush()
            repository = PostgresTextChunkRepository(session)
            await repository.replace(
                first.id,
                [
                    ChunkDraft(
                        page_number=1,
                        chunk_index=0,
                        chunk_type="text",
                        content="Invoice ALPHA-001 grand total IDR 110000",
                        token_count=10,
                    )
                ],
            )
            await repository.replace(
                second.id,
                [
                    ChunkDraft(
                        page_number=1,
                        chunk_index=0,
                        chunk_type="text",
                        content="Invoice ALPHA-001 grand total IDR 999999",
                        token_count=10,
                    )
                ],
            )
            await session.commit()

            results = await repository.search(first.id, "ALPHA-001 grand total", 5)

            assert len(results) == 1
            assert results[0].document_id == first.id
            assert "110000" in results[0].content
            assert "999999" not in results[0].content

            await session.execute(delete(Document).where(Document.id.in_([first.id, second.id])))
            await session.commit()
    finally:
        await engine.dispose()
