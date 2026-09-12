import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.retrieval.chunking import PageAwareChunker
from app.retrieval.repository import PostgresTextChunkRepository
from app.retrieval.schemas import IndexResult, SearchRequest, SearchResponse
from app.retrieval.service import DocumentIndexingService, DocumentSearchService, TextRetriever

router = APIRouter(prefix="/documents", tags=["rag"])


def get_indexing_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentIndexingService:
    repository = PostgresTextChunkRepository(session)
    return DocumentIndexingService(
        session=session,
        chunker=PageAwareChunker(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        ),
        repository=repository,
    )


def get_search_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentSearchService:
    repository = PostgresTextChunkRepository(session)
    return DocumentSearchService(
        session=session,
        retriever=TextRetriever(repository=repository),
    )


@router.post("/{document_id}/index", response_model=IndexResult)
async def index_document(
    document_id: uuid.UUID,
    service: Annotated[DocumentIndexingService, Depends(get_indexing_service)],
) -> IndexResult:
    return await service.index(document_id)


@router.post("/{document_id}/search", response_model=SearchResponse)
async def search_document(
    document_id: uuid.UUID,
    payload: SearchRequest,
    service: Annotated[DocumentSearchService, Depends(get_search_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResponse:
    chunks = await service.search(
        document_id, payload.question, payload.top_k or settings.rag_top_k
    )
    return SearchResponse(query=payload.question, chunks=chunks)
