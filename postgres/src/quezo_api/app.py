from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    scope: Literal["process-only"] = "process-only"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Quezo API scaffold",
        version="0.0.0",
        description="Process liveness only. Assessment features await architecture review.",
    )

    @app.get("/health/live", response_model=LivenessResponse)
    async def liveness() -> LivenessResponse:
        return LivenessResponse()

    return app
