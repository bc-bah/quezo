from datetime import datetime, timedelta
from enum import StrEnum
import re
from typing import Annotated, Generic, TypeVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
)
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=False,
        serialize_by_alias=True,
        extra="forbid",
        hide_input_in_errors=True,
    )


PublicId = UUID
NonNegativeInteger = Annotated[StrictInt, Field(ge=0)]


def _timestamp_input(value: object) -> object:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]+)?(?:[Zz]|\+00:00)",
        value,
    ):
        return value
    raise ValueError("An RFC 3339 timestamp is required")


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("A UTC timestamp is required")
    return value


UtcTimestamp = Annotated[
    AwareDatetime, BeforeValidator(_timestamp_input), AfterValidator(_require_utc)
]


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    AUTHOR = "author"
    LEARNER = "learner"


class AccessStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Actor(ApiModel):
    user_id: PublicId
    roles: list[Role]
    status: AccessStatus


def _query_integer(value: object) -> object:
    # HTTP query parameters are strings; do not coerce booleans or fractions.
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    return value


class PaginationParams(ApiModel):
    page_size: Annotated[
        StrictInt, Field(ge=1, le=100), BeforeValidator(_query_integer)
    ] = 25
    cursor: str | None = None


Item = TypeVar("Item")


class Page(ApiModel, Generic[Item]):
    items: list[Item]
    next_cursor: str | None
