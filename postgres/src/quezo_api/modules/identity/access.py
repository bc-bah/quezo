from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import AsyncConnection

from quezo_api.database import get_database
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.schemas import AccessStatus, Actor, Role
from quezo_api.modules.identity.tokens import TokenVerifier, VerifiedIdentity

bearer = HTTPBearer(auto_error=False)


async def resolve_actor(
    connection: AsyncConnection[tuple[object, ...]], identity: VerifiedIdentity,
) -> Actor:
    cursor = await connection.execute(
        """
        SELECT a.id, a.status,
               ARRAY(SELECT r.role FROM quezo.account_roles r
                     WHERE r.account_id = a.id ORDER BY r.role)
        FROM quezo.identity_mappings m
        JOIN quezo.accounts a ON a.id = m.account_id
        WHERE m.issuer = %s AND m.subject = %s AND m.active
        """,
        (identity.issuer, identity.subject),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED)
    actor = Actor.model_validate({"userId": row[0], "status": row[1], "roles": row[2]})
    if actor.status != AccessStatus.ACTIVE:
        raise ApiError(ErrorCode.ACCOUNT_DISABLED)
    return actor


async def get_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> VerifiedIdentity:
    if credentials is None or len(request.headers.getlist("authorization")) != 1:
        raise ApiError(ErrorCode.UNAUTHENTICATED)
    verifier = getattr(request.app.state, "token_verifier", None)
    if not isinstance(verifier, TokenVerifier):
        raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
    return await verifier.verify(credentials.credentials)


async def get_actor(
    request: Request, identity: Annotated[VerifiedIdentity, Depends(get_identity)],
) -> Actor:
    async with get_database(request).transaction() as connection:
        return await resolve_actor(connection, identity)


def require_role(actor: Actor, role: Role) -> None:
    if actor.status != AccessStatus.ACTIVE:
        raise ApiError(ErrorCode.ACCOUNT_DISABLED)
    if role not in actor.roles:
        raise ApiError(ErrorCode.FORBIDDEN)


def require_owner(actor: Actor, owner_id: UUID | None, role: Role) -> None:
    require_role(actor, role)
    if owner_id != actor.user_id:
        raise ApiError(ErrorCode.NOT_FOUND)
