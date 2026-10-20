import json
import logging
from enum import StrEnum
from typing import get_args
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.routing import APIRoute
from psycopg import OperationalError
from psycopg_pool import PoolTimeout, TooManyRequests
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from quezo_api.schemas import ApiModel

MAX_BODY_BYTES = 256 * 1024
logger = logging.getLogger("quezo_api.http")


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    CSRF_REJECTED = "CSRF_REJECTED"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    RESPONSE_REVISION_CONFLICT = "RESPONSE_REVISION_CONFLICT"
    DRAFT_REVISION_CONFLICT = "DRAFT_REVISION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ATTEMPT_FINALIZED = "ATTEMPT_FINALIZED"
    DEADLINE_PASSED = "DEADLINE_PASSED"
    ATTEMPT_LIMIT_REACHED = "ATTEMPT_LIMIT_REACHED"
    ASSESSMENT_UNAVAILABLE = "ASSESSMENT_UNAVAILABLE"
    INVALID_STATE = "INVALID_STATE"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


ERRORS: dict[ErrorCode, tuple[int, str]] = {
    ErrorCode.UNAUTHENTICATED: (401, "Authentication is required."),
    ErrorCode.FORBIDDEN: (403, "This operation is not permitted."),
    ErrorCode.ACCOUNT_DISABLED: (403, "Account access is disabled."),
    ErrorCode.CSRF_REJECTED: (403, "The request origin could not be verified."),
    ErrorCode.NOT_FOUND: (404, "The resource was not found."),
    ErrorCode.METHOD_NOT_ALLOWED: (405, "This method is not allowed."),
    ErrorCode.RESPONSE_REVISION_CONFLICT: (409, "This answer changed in another session."),
    ErrorCode.DRAFT_REVISION_CONFLICT: (409, "This draft changed in another session."),
    ErrorCode.IDEMPOTENCY_CONFLICT: (409, "This request identifier was already used."),
    ErrorCode.ATTEMPT_FINALIZED: (409, "This attempt is already finalized."),
    ErrorCode.DEADLINE_PASSED: (409, "The attempt deadline has passed."),
    ErrorCode.ATTEMPT_LIMIT_REACHED: (409, "The attempt limit has been reached."),
    ErrorCode.ASSESSMENT_UNAVAILABLE: (409, "This assessment is unavailable."),
    ErrorCode.INVALID_STATE: (409, "This operation is not valid in the current state."),
    ErrorCode.PAYLOAD_TOO_LARGE: (413, "The request body exceeds 256 KiB."),
    ErrorCode.VALIDATION_FAILED: (422, "The request is invalid."),
    ErrorCode.RATE_LIMITED: (429, "Too many requests."),
    ErrorCode.DEPENDENCY_UNAVAILABLE: (503, "A required service is unavailable."),
    ErrorCode.INTERNAL_ERROR: (500, "An internal error occurred."),
}


class ValidationReason(StrEnum):
    REQUIRED = "required"
    UNKNOWN_FIELD = "unknown_field"
    INVALID_VALUE = "invalid_value"


class FieldError(ApiModel):
    path: list[str | int]
    reason: ValidationReason


class ValidationDetails(ApiModel):
    fields: list[FieldError]


class ErrorEnvelope(ApiModel):
    code: ErrorCode
    message: str
    request_id: UUID
    details: ValidationDetails | None = None


class ApiError(Exception):
    def __init__(self, code: ErrorCode, *, retry_after: int | None = None) -> None:
        if retry_after is not None and (
            code != ErrorCode.RATE_LIMITED
            or type(retry_after) is not int
            or retry_after < 1
        ):
            raise ValueError("Retry-After requires RATE_LIMITED and positive seconds")
        super().__init__(code.value)
        self.code = code
        self.retry_after = retry_after


def error_response(
    request_id: str,
    code: ErrorCode,
    *,
    details: ValidationDetails | None = None,
    headers: dict[str, str] | None = None,
    status: int | None = None,
) -> JSONResponse:
    default_status, message = ERRORS[code]
    status = default_status if status is None else status
    logger.log(
        logging.ERROR if status >= 500 else logging.INFO,
        json.dumps({"requestId": request_id, "code": code.value, "status": status}),
    )
    envelope = ErrorEnvelope.model_validate({
        "code": code, "message": message, "requestId": request_id, "details": details,
    })
    return JSONResponse(
        status_code=status,
        content=envelope.model_dump(mode="json", exclude_none=True),
        headers={
            **(headers or {}),
            "X-Request-ID": request_id,
            "Cache-Control": "private, no-store",
        },
    )


def _model_field_names(annotation: object, seen: set[type[BaseModel]]) -> set[str]:
    names: set[str] = set()
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if annotation in seen:
            return names
        seen.add(annotation)
        for name, field in annotation.model_fields.items():
            names.add(field.alias or name)
            names.update(_model_field_names(field.annotation, seen))
    for argument in get_args(annotation):
        names.update(_model_field_names(argument, seen))
    return names


def _safe_validation_details(
    request: Request, exception: RequestValidationError
) -> ValidationDetails:
    names: set[str] = set()
    route = request.scope.get("route")
    if isinstance(route, APIRoute):
        # Only schema-owned names may be reflected, never unknown keys or union tags.
        pending = [route.dependant]
        while pending:
            dependency = pending.pop()
            pending.extend(dependency.dependencies)
            for field in (
                *dependency.body_params, *dependency.query_params,
                *dependency.path_params, *dependency.header_params,
                *dependency.cookie_params,
            ):
                names.add(field.alias)
                names.update(_model_field_names(field.field_info.annotation, set()))
    fields: list[FieldError] = []
    for error in exception.errors():
        path: list[str | int] = []
        for index, part in enumerate(error["loc"]):
            if isinstance(part, int):
                path.append(part)
            elif part in names or (
                index == 0 and part in {"body", "query", "path", "header", "cookie"}
            ):
                path.append(part)
            else:
                path.append("[field]")
        reason = {
            "missing": ValidationReason.REQUIRED,
            "extra_forbidden": ValidationReason.UNKNOWN_FIELD,
        }.get(error["type"], ValidationReason.INVALID_VALUE)
        fields.append(FieldError(path=path, reason=reason))
    return ValidationDetails(fields=fields)


async def validation_handler(request: Request, exception: Exception) -> JSONResponse:
    assert isinstance(exception, RequestValidationError)
    return error_response(
        request.state.request_id, ErrorCode.VALIDATION_FAILED,
        details=_safe_validation_details(request, exception),
    )


async def api_error_handler(request: Request, exception: Exception) -> JSONResponse:
    assert isinstance(exception, ApiError)
    headers = (
        {"Retry-After": str(exception.retry_after)}
        if exception.retry_after is not None else None
    )
    return error_response(request.state.request_id, exception.code, headers=headers)


async def http_error_handler(request: Request, exception: Exception) -> JSONResponse:
    assert isinstance(exception, HTTPException)
    code = {
        400: ErrorCode.VALIDATION_FAILED,
        401: ErrorCode.UNAUTHENTICATED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.INVALID_STATE,
        413: ErrorCode.PAYLOAD_TOO_LARGE,
        422: ErrorCode.VALIDATION_FAILED,
        429: ErrorCode.RATE_LIMITED,
        503: ErrorCode.DEPENDENCY_UNAVAILABLE,
    }.get(exception.status_code, ErrorCode.INTERNAL_ERROR)
    headers: dict[str, str] = {}
    for name, value in (exception.headers or {}).items():
        if name.lower() == "allow":
            methods = [method.strip() for method in value.split(",")]
            if all(m in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"} for m in methods):
                headers["Allow"] = ", ".join(methods)
        elif name.lower() == "retry-after" and value.isascii() and value.isdecimal():
            headers["Retry-After"] = value
    return error_response(
        request.state.request_id, code, headers=headers,
        status=400 if exception.status_code == 400 else None,
    )


async def dependency_error_handler(request: Request, exception: Exception) -> JSONResponse:
    return error_response(request.state.request_id, ErrorCode.DEPENDENCY_UNAVAILABLE)


async def response_error_handler(request: Request, exception: Exception) -> JSONResponse:
    return error_response(request.state.request_id, ErrorCode.INTERNAL_ERROR)


class HttpBoundary:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False

        async def correlated_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [
                    (name, value) for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    await error_response(
                        request_id, ErrorCode.PAYLOAD_TOO_LARGE
                    )(scope, receive, correlated_send)
                    return
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay_receive, correlated_send)
        except Exception:
            # Catch here, not ServerErrorMiddleware: it re-raises to Uvicorn, which
            # would log the original exception (possibly containing request data).
            response = error_response(request_id, ErrorCode.INTERNAL_ERROR)
            if started:
                raise RuntimeError("Response failed after headers; see correlated error log") from None
            await response(scope, receive, correlated_send)


def install_error_handling(app: FastAPI) -> None:
    app.add_middleware(HttpBoundary)
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(ResponseValidationError, response_error_handler)
    for exception_type in (OperationalError, PoolTimeout, TooManyRequests):
        app.add_exception_handler(exception_type, dependency_error_handler)
