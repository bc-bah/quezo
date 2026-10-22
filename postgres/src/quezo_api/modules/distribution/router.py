from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.distribution import service
from quezo_api.modules.distribution.schemas import Assignment, AssignmentCreate, EligibleLearner
from quezo_api.modules.identity.access import get_identity, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.schemas import Actor, Page, PaginationParams

router = APIRouter(prefix="/api/v1", tags=["distribution"], responses={
    **{status: {"model": ErrorEnvelope} for status in (401, 403, 404, 409, 503)},
    422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
})


async def transaction(
    request: Request, response: Response,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> AsyncIterator[tuple[Connection, Actor]]:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        yield connection, await resolve_actor(connection, identity)


Transaction = Annotated[tuple[Connection, Actor], Depends(transaction, scope="function")]


@router.get("/eligible-learners")
async def learners(tx: Transaction, page: Annotated[PaginationParams, Query()]) -> Page[EligibleLearner]:
    return await service.eligible_learners(*tx, page)


@router.post("/assignments", status_code=201, responses={200: {"model": Assignment}})
async def assign(
    tx: Transaction, body: AssignmentCreate, response: Response,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Assignment:
    assignment, created = await service.assign(*tx, body, identity)
    response.status_code = 201 if created else 200
    return assignment


@router.get("/assignments")
async def assignments(tx: Transaction, page: Annotated[PaginationParams, Query()]) -> Page[Assignment]:
    return await service.list_assignments(*tx, page)


@router.get("/assignments/{assignment_id}")
async def assignment(tx: Transaction, assignment_id: UUID) -> Assignment:
    return await service.get_assignment(*tx, assignment_id)
