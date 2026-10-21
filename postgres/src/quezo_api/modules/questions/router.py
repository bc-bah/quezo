from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.identity.access import get_identity, require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions import service
from quezo_api.modules.questions.schemas import (
    Bank, BankWrite, QuestionCreate, QuestionEdit, QuestionListParams,
    QuestionSummary, QuestionVersion,
)
from quezo_api.schemas import Actor, Page, PaginationParams, Role

router = APIRouter(
    prefix="/api/v1", tags=["questions"],
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
        # Preserve the contract across Python's differing HTTP 422 reason phrases.
        422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
        503: {"model": ErrorEnvelope},
    },
)


async def author_transaction(
    request: Request, response: Response,
    identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> AsyncIterator[tuple[service.Connection, Actor]]:
    response.headers["Cache-Control"] = "private, no-store"
    async with get_database(request).transaction() as connection:
        actor = await resolve_actor(connection, identity)
        require_role(actor, Role.AUTHOR)
        yield connection, actor


# Function scope commits (including deferred constraints) before the response is sent.
Transaction = Annotated[tuple[service.Connection, Actor], Depends(author_transaction, scope="function")]


@router.get("/question-banks")
async def banks(tx: Transaction, page: Annotated[PaginationParams, Query()]) -> Page[Bank]:
    return await service.list_banks(*tx, page)


@router.post("/question-banks", status_code=201)
async def create_bank(tx: Transaction, body: BankWrite) -> Bank:
    return await service.write_bank(*tx, body)


@router.get("/question-banks/{bank_id}")
async def bank(tx: Transaction, bank_id: UUID) -> Bank:
    return await service.get_bank(*tx, bank_id)


@router.patch("/question-banks/{bank_id}")
async def edit_bank(tx: Transaction, bank_id: UUID, body: BankWrite) -> Bank:
    return await service.write_bank(*tx, body, bank_id)


@router.get("/questions")
async def questions(tx: Transaction, page: Annotated[QuestionListParams, Query()]) -> Page[QuestionSummary]:
    return await service.list_questions(*tx, page)


@router.post("/questions", status_code=201)
async def create_question(tx: Transaction, body: QuestionCreate) -> QuestionVersion:
    return await service.create_question(*tx, body)


@router.get("/questions/{question_id}")
async def question(tx: Transaction, question_id: UUID) -> QuestionVersion:
    return await service.get_question(*tx, question_id)


@router.patch("/questions/{question_id}")
async def edit_question(tx: Transaction, question_id: UUID, body: QuestionEdit) -> QuestionVersion:
    return await service.edit_question(*tx, question_id, body)


@router.get("/questions/{question_id}/versions")
async def versions(
    tx: Transaction, question_id: UUID, page: Annotated[PaginationParams, Query()],
) -> Page[QuestionSummary]:
    return await service.list_versions(*tx, question_id, page)


@router.get("/questions/{question_id}/versions/{version_id}")
async def version(tx: Transaction, question_id: UUID, version_id: UUID) -> QuestionVersion:
    return await service.get_question(*tx, question_id, version_id)
