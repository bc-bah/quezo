import pytest

from quezo_api.database import DatabaseSettings


def test_database_configuration_requires_an_explicit_runtime_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("QUEZO_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="QUEZO_DATABASE_URL"):
        DatabaseSettings.from_env()

    monkeypatch.setenv(
        "QUEZO_DATABASE_URL",
        "postgresql://quezo_runtime:synthetic-secret@127.0.0.1:5432/quezo",
    )
    settings = DatabaseSettings.from_env()
    assert settings.pool_min == 1
    assert settings.pool_max == 5
    assert "synthetic-secret" not in repr(settings)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("QUEZO_DATABASE_URL", "sqlite:///:memory:"),
        ("QUEZO_DATABASE_URL", "postgresql://postgres:synthetic-secret@localhost/quezo"),
        ("QUEZO_DATABASE_URL", "postgresql://quezo_runtime:synthetic-secret@localhost"),
        ("QUEZO_DB_POOL_MIN", "6"),
        ("QUEZO_DB_POOL_MAX", "0"),
        ("QUEZO_DB_POOL_MAX", "21"),
        ("QUEZO_DB_POOL_TIMEOUT", "nan"),
        ("QUEZO_DB_STARTUP_TIMEOUT", "0"),
        ("QUEZO_DB_STATEMENT_TIMEOUT_MS", "0"),
    ],
)
def test_invalid_configuration_fails_without_disclosing_credentials(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(
        "QUEZO_DATABASE_URL",
        "postgresql://quezo_runtime:synthetic-secret@127.0.0.1:5432/quezo",
    )
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError) as error:
        DatabaseSettings.from_env()
    assert "synthetic-secret" not in str(error.value)
