from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from starlette import status

from quezo_api.database import Database, get_database
from quezo_api.errors import ApiError, ErrorCode, ErrorEnvelope
from quezo_api.modules.identity.access import get_actor, require_role
from quezo_api.modules.identity.account_admin import KeycloakAccountAdmin
from quezo_api.modules.identity.accounts import (
    list_accounts,
    provision_account,
    update_roles,
    update_status,
)
from quezo_api.schemas import (
    AccountAdminPage,
    AccountAdminView,
    AccountProvisionRequest,
    AccountRoleUpdate,
    Actor,
    Role,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])


@router.get(
    "/me", response_model=Actor,
    responses={
        401: {"model": ErrorEnvelope},
        403: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
    },
)
async def me(response: Response, actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
    response.headers["Cache-Control"] = "private, no-store"
    return actor


def _admin_provider(request: Request) -> KeycloakAccountAdmin:
    provider = getattr(request.app.state, "account_admin", None)
    if not isinstance(provider, KeycloakAccountAdmin):
        raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
    return provider


@router.get(
    "/admin/accounts", response_model=AccountAdminPage,
    responses={401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope}},
)
async def accounts(
    request: Request,
    response: Response,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AccountAdminPage:
    require_role(actor, Role.ADMINISTRATOR)
    response.headers["Cache-Control"] = "private, no-store"
    return await list_accounts(get_database(request))


@router.post(
    "/admin/accounts", response_model=AccountAdminView, status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        409: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
        503: {"model": ErrorEnvelope},
    },
)
async def create_account(
    request: Request,
    body: AccountProvisionRequest,
    response: Response,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AccountAdminView:
    require_role(actor, Role.ADMINISTRATOR)
    provider = _admin_provider(request)
    response.headers["Cache-Control"] = "private, no-store"
    return await provision_account(
        get_database(request), provider, provider.settings.issuer, actor, body,
    )


@router.put(
    "/admin/accounts/{account_id}/roles", response_model=AccountAdminView,
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
    },
)
async def change_account_roles(
    account_id: UUID,
    body: AccountRoleUpdate,
    response: Response,
    request: Request,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AccountAdminView:
    require_role(actor, Role.ADMINISTRATOR)
    response.headers["Cache-Control"] = "private, no-store"
    return await update_roles(get_database(request), actor, account_id, body)


@router.post(
    "/admin/accounts/{account_id}/activate", response_model=AccountAdminView,
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
        503: {"model": ErrorEnvelope},
    },
)
async def activate_account(
    account_id: UUID,
    request: Request,
    response: Response,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AccountAdminView:
    require_role(actor, Role.ADMINISTRATOR)
    response.headers["Cache-Control"] = "private, no-store"
    return await update_status(
        get_database(request), _admin_provider(request), actor, account_id, True,
    )


@router.post(
    "/admin/accounts/{account_id}/deactivate", response_model=AccountAdminView,
    responses={
        401: {"model": ErrorEnvelope}, 403: {"model": ErrorEnvelope},
        404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope, "description": "Unprocessable Entity"},
        503: {"model": ErrorEnvelope},
    },
)
async def deactivate_account(
    account_id: UUID,
    request: Request,
    response: Response,
    actor: Annotated[Actor, Depends(get_actor)],
) -> AccountAdminView:
    require_role(actor, Role.ADMINISTRATOR)
    response.headers["Cache-Control"] = "private, no-store"
    return await update_status(
        get_database(request), _admin_provider(request), actor, account_id, False,
    )
