from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.identity.access import get_identity
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.results import service
from quezo_api.modules.results.schemas import AttemptHistoryItem, FinalizedSubmission, LearnerResult, QuizReport
from quezo_api.schemas import Page, PaginationParams

router = APIRouter(prefix="/api/v1", tags=["results"], responses={
    **{status: {"model": ErrorEnvelope} for status in (401, 403, 404, 409, 503)},
    422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
})


@router.get("/attempts/{attempt_id}/result")
async def result(
    request: Request, response: Response, attempt_id: UUID,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> LearnerResult:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        projection = await service.get_result(connection, identity, attempt_id)
    return projection


@router.get("/me/attempts")
async def history(
    request: Request, response: Response, page: Annotated[PaginationParams, Query()],
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Page[AttemptHistoryItem]:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        return await service.learner_history(connection, identity, page)


@router.get("/quizzes/{quiz_id}/results")
async def report(
    request: Request, response: Response, quiz_id: UUID, page: Annotated[PaginationParams, Query()],
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> QuizReport:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        await connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return await service.quiz_report(connection, identity, quiz_id, page)


@router.get("/quizzes/{quiz_id}/results/attempts")
async def report_attempts(
    request: Request, response: Response, quiz_id: UUID, page: Annotated[PaginationParams, Query()],
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Page[AttemptHistoryItem]:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        return await service.author_attempts(connection, identity, quiz_id, page)


@router.get("/quizzes/{quiz_id}/results/attempts/{attempt_id}")
async def submission(
    request: Request, response: Response, quiz_id: UUID, attempt_id: UUID,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> FinalizedSubmission:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        return await service.finalized_submission(connection, identity, quiz_id, attempt_id)
