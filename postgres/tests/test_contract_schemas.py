from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from quezo_api.schemas import (
    Actor, NonNegativeInteger, Page, PaginationParams, PublicId, UtcTimestamp,
)

USER_ID = "b852a646-70ed-4ab9-aae4-d7fc2e0ca313"


def test_actor_is_minimal_camel_case_and_supports_combined_roles() -> None:
    data = {
        "userId": USER_ID, "roles": ["administrator", "author", "learner"],
        "status": "active",
    }
    actor = Actor.model_validate(data)
    assert actor.user_id == UUID(USER_ID)
    assert actor.model_dump(mode="json") == data
    assert Actor.model_validate({**data, "status": "disabled"}).status == "disabled"
    assert Actor.model_validate({**data, "roles": []}).roles == []


@pytest.mark.parametrize("change", [
    {"userId": "not-a-uuid"}, {"roles": ["superuser"]}, {"status": "pending"},
    {"roles": "author"}, {"email": "synthetic@example.invalid"},
    {"user_id": USER_ID}, {"token": "synthetic-secret"},
])
def test_actor_rejects_malformed_or_extra_fields(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Actor.model_validate({
            "userId": USER_ID, "roles": ["learner"], "status": "active", **change,
        })


@pytest.mark.parametrize("value", [True, 1.0, 1.2, "1", -1])
def test_nonnegative_integer_does_not_coerce(value: object) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(NonNegativeInteger).validate_python(value)


def test_uuid_and_integer_roundtrip() -> None:
    assert TypeAdapter(PublicId).dump_json(UUID(USER_ID)) == f'"{USER_ID}"'.encode()
    assert TypeAdapter(NonNegativeInteger).validate_python(0) == 0


@pytest.mark.parametrize("value", [
    "2026-10-20T14:00:00", "2026-10-20T14:00:00+01:00", "2026-10-20",
    "invalid", 1_792_509_600, "1792509600",
    "2026-10-20T14:00:00+0000", "2026-10-20T14:00:00-00:00",
    "2026-10-20T14:00Z",
])
def test_timestamp_rejects_missing_or_non_utc_zone_and_epoch(value: object) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(UtcTimestamp).validate_python(value)


def test_utc_timestamp_roundtrip() -> None:
    adapter = TypeAdapter(UtcTimestamp)
    instant = datetime(2026, 10, 20, 14, tzinfo=timezone.utc)
    assert adapter.validate_python("2026-10-20T14:00:00Z") == instant
    assert adapter.validate_python("2026-10-20T14:00:00+00:00") == instant
    assert adapter.validate_python("2026-10-20t14:00:00z") == instant
    assert adapter.dump_json(instant) == b'"2026-10-20T14:00:00Z"'


@pytest.mark.parametrize("value", [1, 100, "1", "100"])
def test_pagination_bounds(value: object) -> None:
    page = PaginationParams.model_validate({"pageSize": value})
    assert page.page_size == int(str(value))


@pytest.mark.parametrize("value", [0, 101, -1, 1.5, True, None, "1.0", "invalid"])
def test_pagination_rejects_invalid_sizes(value: object) -> None:
    with pytest.raises(ValidationError):
        PaginationParams.model_validate({"pageSize": value})


def test_pagination_defaults_and_exhaustion_shape() -> None:
    assert PaginationParams().model_dump() == {"pageSize": 25, "cursor": None}
    assert Page[Actor].model_validate({
        "items": [], "nextCursor": None,
    }).model_dump(mode="json") == {"items": [], "nextCursor": None}
    with pytest.raises(ValidationError):
        PaginationParams.model_validate({"page_size": 50})
    with pytest.raises(ValidationError):
        Page[Actor].model_validate({"items": []})
