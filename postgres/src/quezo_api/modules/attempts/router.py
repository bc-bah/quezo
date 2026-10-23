from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ApiError, ErrorEnvelope
from quezo_api.modules.attempts import finalization, responses, service
from quezo_api.modules.attempts.schemas import Attempt, Completion, SaveCommand, SaveResult, StartCommand, SubmissionCommand
from quezo_api.modules.identity.access import get_identity
from quezo_api.modules.identity.tokens import VerifiedIdentity

router = APIRouter(prefix="/api/v1", tags=["attempts"], responses={
    **{status: {"model": ErrorEnvelope} for status in (401, 403, 404, 409, 503)},
    422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
})


@router.post("/assignments/{assignment_id}/attempts", status_code=201, responses={200: {"model": Attempt}})
async def start(
    request: Request, response: Response, assignment_id: UUID, body: StartCommand,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
    idempotency_key: Annotated[UUID, Header()],
) -> Attempt:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        attempt, created = await service.start(connection, identity, assignment_id, body, idempotency_key)
    response.status_code = 201 if created else 200
    return attempt


@router.get("/attempts/{attempt_id}")
async def attempt(
    request: Request, response: Response, attempt_id: UUID,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Attempt:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        result = await service.get_attempt(connection, identity, attempt_id)
    return result


@router.post("/attempts/{attempt_id}/submission")
async def submit(
    request: Request, response: Response, attempt_id: UUID, body: SubmissionCommand,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Completion:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        result = await finalization.submit(connection, identity, attempt_id)
    return result


@router.put("/attempts/{attempt_id}/responses/{question_id}")
async def save_response(
    request: Request, response: Response, attempt_id: UUID, question_id: UUID, body: SaveCommand,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> SaveResult:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        result = await responses.save(connection, identity, attempt_id, question_id, body)
    if isinstance(result, ApiError):
        raise result
    return result
