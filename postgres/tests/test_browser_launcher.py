import os

import pytest

from run_browser import runtime_environment, unused_ports


def test_browser_launcher_never_passes_ambient_credentials_to_apps(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "QUEZO_MIGRATION_URL", "QUEZO_TEST_ADMIN_URL", "QUEZO_WEB_DATABASE_URL",
        "KEYCLOAK_ADMIN_PASSWORD", "QUEZO_SYNTHETIC_PASSWORD", "PGSERVICE",
        "NEXT_PUBLIC_TOKEN", "DOCKER_HOST", "COMPOSE_FILE",
    ):
        monkeypatch.setenv(name, "must-not-inherit")
    env = runtime_environment()
    assert "must-not-inherit" not in env.values()
    assert env.get("PATH") == os.environ.get("PATH")


def test_browser_launcher_allocates_distinct_loopback_ports() -> None:
    ports = unused_ports()
    assert len(set(ports)) == 4
    assert all(0 < port <= 65535 for port in ports)
