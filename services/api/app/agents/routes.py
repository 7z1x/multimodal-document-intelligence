import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import AgentResponse, AskRequest, RagRunRead
from app.agents.service import AgenticRagService
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.generation.opencode import OpenCodeRagModel
from app.observability.exporter import get_trace_exporter
from app.observability.service import ObservabilityService
from app.providers.opencode import OpenCodeStructuredClient
from app.reranking.opencode import OpenCodeReranker
from app.retrieval.repository import PostgresTextChunkRepository
from app.retrieval.service import TextRetriever

router = APIRouter(prefix="/documents", tags=["agentic-rag"])


def get_agent_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgenticRagService:
    repository = PostgresTextChunkRepository(session)
    client = OpenCodeStructuredClient(
        base_url=settings.opencode_base_url,
        provider=settings.opencode_provider,
        model=settings.opencode_model,
        directory=settings.opencode_directory,
        timeout_seconds=settings.opencode_timeout_seconds,
    )
    return AgenticRagService(
        session=session,
        retriever=TextRetriever(repository=repository),
        reranker=OpenCodeReranker(
            client,
            model_weight=settings.rag_rerank_model_weight,
        ),
        model=OpenCodeRagModel(client),
        top_k=settings.rag_top_k,
        min_relevance=settings.rag_min_relevance,
        max_attempts=settings.agent_max_retrieval_attempts,
        observability=ObservabilityService(
            session=session,
            exporter=get_trace_exporter(),
            audit_log_dir=settings.audit_log_dir,
        ),
    )


@router.post("/{document_id}/ask", response_model=AgentResponse)
async def ask_document(
    document_id: uuid.UUID,
    payload: AskRequest,
    service: Annotated[AgenticRagService, Depends(get_agent_service)],
) -> AgentResponse:
    return await service.ask(document_id, payload.question)


@router.get("/{document_id}/rag-runs", response_model=list[RagRunRead])
async def get_rag_runs(
    document_id: uuid.UUID,
    service: Annotated[AgenticRagService, Depends(get_agent_service)],
) -> list[RagRunRead]:
    return await service.runs(document_id)
