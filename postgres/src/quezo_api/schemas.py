from datetime import datetime, timedelta
from enum import StrEnum
import re
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    model_validator,
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


class AccountProvisionRequest(ApiModel):
    username: Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9._@+-]+$")]
    email: Annotated[str | None, Field(max_length=254)] = None
    roles: Annotated[list[Role], Field(max_length=3)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_request(self) -> "AccountProvisionRequest":
        if self.email is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            raise ValueError("A valid email address is required")
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("Roles must be unique")
        self.username = self.username.lower()
        return self


class AccountRoleUpdate(ApiModel):
    roles: Annotated[list[Role], Field(max_length=3)]

    @model_validator(mode="after")
    def validate_request(self) -> "AccountRoleUpdate":
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("Roles must be unique")
        return self


ProvisioningState = Literal["pending", "complete", "failed"]
IdentitySyncState = Literal["in_sync", "pending", "failed"]


class AccountAdminView(ApiModel):
    user_id: PublicId
    username: str | None
    email: str | None
    status: AccessStatus
    roles: list[Role]
    provisioning_state: ProvisioningState
    provisioning_error_code: str | None
    identity_sync_state: IdentitySyncState
    identity_error_code: str | None


class AccountAdminPage(ApiModel):
    items: list[AccountAdminView]
    next_cursor: str | None = None


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
