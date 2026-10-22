from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.attempts import service
from quezo_api.modules.attempts.schemas import Attempt, StartCommand
from quezo_api.modules.distribution.router import Transaction
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
async def attempt(tx: Transaction, attempt_id: UUID) -> Attempt:
    return await service.get_attempt(*tx, attempt_id)
