from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from quezo_api.database import get_database
from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.identity.access import get_identity, require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.quizzes import service
from quezo_api.modules.quizzes.schemas import (
    DraftCommand, DraftEdit, PublishedQuiz, PublishAcknowledgement, Quiz,
    QuizComposition, QuizPreview, QuizSummary,
)
from quezo_api.schemas import Actor, Page, PaginationParams, Role

router = APIRouter(
    prefix="/api/v1/quizzes", tags=["quizzes"],
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
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


Transaction = Annotated[tuple[service.Connection, Actor], Depends(author_transaction, scope="function")]


@router.get("")
async def quizzes(tx: Transaction, page: Annotated[PaginationParams, Query()]) -> Page[QuizSummary]:
    return await service.list_quizzes(*tx, page)


@router.post("", status_code=201)
async def create(tx: Transaction, body: QuizComposition) -> Quiz:
    return await service.create_quiz(*tx, body)


@router.get("/{quiz_id}")
async def quiz(tx: Transaction, quiz_id: UUID) -> Quiz:
    return await service.get_quiz(*tx, quiz_id)


@router.patch("/{quiz_id}")
async def edit(tx: Transaction, quiz_id: UUID, body: DraftEdit) -> Quiz:
    return await service.edit_draft(*tx, quiz_id, body)


@router.post("/{quiz_id}/drafts", status_code=201)
async def new_draft(tx: Transaction, quiz_id: UUID, body: DraftCommand) -> Quiz:
    return await service.new_draft(*tx, quiz_id, body)


@router.post("/{quiz_id}/preview")
async def preview(tx: Transaction, quiz_id: UUID, body: DraftCommand) -> QuizPreview:
    return await service.preview(*tx, quiz_id, body)


@router.post("/{quiz_id}/publish", status_code=201, responses={200: {"model": PublishAcknowledgement}})
async def publish(
    tx: Transaction, quiz_id: UUID, body: DraftCommand, response: Response, request: Request,
    idempotency_key: Annotated[UUID, Header()],
) -> PublishAcknowledgement:
    acknowledgement, created = await service.publish(
        *tx, quiz_id, body, idempotency_key, UUID(request.state.request_id),
    )
    response.status_code = 201 if created else 200
    return acknowledgement


@router.get("/{quiz_id}/versions/{version_id}")
async def version(tx: Transaction, quiz_id: UUID, version_id: UUID) -> PublishedQuiz:
    return await service.get_version(*tx, quiz_id, version_id)
