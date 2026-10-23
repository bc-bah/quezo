from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.identity.access import get_identity
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.results import service
from quezo_api.modules.results.schemas import LearnerResult

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
