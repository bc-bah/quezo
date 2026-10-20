from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic.json_schema import models_json_schema

from quezo_api.schemas import Actor, PaginationParams


class ContractAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            document = get_openapi(
                title=self.title, version=self.version,
                description=self.description, routes=self.routes,
            )
            _, shared = models_json_schema(
                [(Actor, "serialization"), (PaginationParams, "validation")],
                by_alias=True, ref_template="#/components/schemas/{model}",
            )
            document.setdefault("components", {}).setdefault("schemas", {}).update(
                shared["$defs"]
            )
            for path in document["paths"].values():
                for operation in path.values():
                    for response in operation["responses"].values():
                        response.setdefault("headers", {})["X-Request-ID"] = {
                            "description": "Server-generated HTTP correlation UUID; not an idempotency key.",
                            "schema": {"type": "string", "format": "uuid"},
                        }
            self.openapi_schema = document
        return self.openapi_schema
