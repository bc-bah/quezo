from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
import httpx2 as httpx

from quezo_api.database import Database, DatabaseSettings
from quezo_api.errors import ErrorEnvelope, install_error_handling
from quezo_api.openapi import ContractAPI
from quezo_api.modules.identity.router import router as identity_router
from quezo_api.modules.questions.router import router as questions_router
from quezo_api.modules.quizzes.router import router as quizzes_router
from quezo_api.modules.distribution.router import router as distribution_router
from quezo_api.modules.attempts.router import router as attempts_router
from quezo_api.modules.attempts.expiration import expiration_lifespan
from quezo_api.modules.identity.tokens import IdentitySettings, TokenVerifier


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = IdentitySettings.from_env()
    async with Database(DatabaseSettings.from_env()) as database, httpx.AsyncClient(
        timeout=settings.timeout, trust_env=False, follow_redirects=False,
        limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
    ) as identity_client:
        app.state.database = database
        app.state.token_verifier = TokenVerifier(settings, identity_client)
        async with expiration_lifespan(database):
            yield


class LivenessResponse(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    status: Literal["ok"] = "ok"
    scope: Literal["process-only"] = "process-only"


def create_app() -> FastAPI:
    app = ContractAPI(
        title="Quezo API",
        version="0.0.0",
        description="Process liveness, current identity, versioned questions, quiz publication, assignment and attempt start.",
        lifespan=lifespan,
        responses={"default": {"model": ErrorEnvelope, "description": "Sanitized error"}},
    )
    install_error_handling(app)
    app.include_router(identity_router)
    app.include_router(questions_router)
    app.include_router(quizzes_router)
    app.include_router(distribution_router)
    app.include_router(attempts_router)

    @app.get("/health/live", response_model=LivenessResponse)
    async def liveness() -> LivenessResponse:
        return LivenessResponse()

    return app
