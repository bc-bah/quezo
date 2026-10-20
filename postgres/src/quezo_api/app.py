from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from quezo_api.database import Database, DatabaseSettings
from quezo_api.errors import ErrorEnvelope, install_error_handling
from quezo_api.openapi import ContractAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with Database(DatabaseSettings.from_env()) as database:
        app.state.database = database
        yield


class LivenessResponse(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    status: Literal["ok"] = "ok"
    scope: Literal["process-only"] = "process-only"


def create_app() -> FastAPI:
    app = ContractAPI(
        title="Quezo API scaffold",
        version="0.0.0",
        description="Process liveness only. Assessment features await architecture review.",
        lifespan=lifespan,
        responses={"default": {"model": ErrorEnvelope, "description": "Sanitized error"}},
    )
    install_error_handling(app)

    @app.get("/health/live", response_model=LivenessResponse)
    async def liveness() -> LivenessResponse:
        return LivenessResponse()

    return app
