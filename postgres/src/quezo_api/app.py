from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from quezo_api.database import Database, DatabaseSettings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with Database(DatabaseSettings.from_env()) as database:
        app.state.database = database
        yield


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    scope: Literal["process-only"] = "process-only"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Quezo API scaffold",
        version="0.0.0",
        description="Process liveness only. Assessment features await architecture review.",
        lifespan=lifespan,
    )

    @app.get("/health/live", response_model=LivenessResponse)
    async def liveness() -> LivenessResponse:
        return LivenessResponse()

    return app
