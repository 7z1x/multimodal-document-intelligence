import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.evaluation.opencode import OpenCodeEvaluationJudge
from app.evaluation.schemas import EvaluationBatchRead, EvaluationRequest
from app.evaluation.service import EvaluationService
from app.providers.opencode import OpenCodeStructuredClient

router = APIRouter(prefix="/documents", tags=["evaluation"])


def get_evaluation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EvaluationService:
    client = OpenCodeStructuredClient(
        base_url=settings.opencode_base_url,
        provider=settings.opencode_provider,
        model=settings.opencode_model,
        directory=settings.opencode_directory,
        timeout_seconds=settings.opencode_timeout_seconds,
    )
    return EvaluationService(session=session, judge=OpenCodeEvaluationJudge(client))


@router.post(
    "/{document_id}/rag-runs/{rag_run_id}/evaluate",
    response_model=EvaluationBatchRead,
)
async def evaluate_rag_run(
    document_id: uuid.UUID,
    rag_run_id: uuid.UUID,
    payload: EvaluationRequest,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationBatchRead:
    return await service.evaluate(document_id, rag_run_id, payload)


@router.get("/{document_id}/evaluations", response_model=list[EvaluationBatchRead])
async def get_evaluations(
    document_id: uuid.UUID,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> list[EvaluationBatchRead]:
    return await service.batches(document_id)
