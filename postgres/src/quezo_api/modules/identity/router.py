from typing import Annotated

from fastapi import APIRouter, Depends, Response

from quezo_api.errors import ErrorEnvelope
from quezo_api.modules.identity.access import get_actor
from quezo_api.schemas import Actor

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
