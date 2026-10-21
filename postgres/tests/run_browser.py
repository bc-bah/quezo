"""Own disposable I02 services; never reuse a development database or realm."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import httpx2 as httpx
from pydantic import SecretStr

from db_helpers import IsolatedDatabase, isolated_database, run_migrations
from keycloak_helpers import KeycloakLocal
from quezo_api.database import Database, DatabaseSettings, database_loop_factory
from quezo_api.modules.identity.provisioning import ACCOUNTS, provision_account

ROOT = Path(__file__).resolve().parents[2]


def unused_ports() -> list[int]:
    sockets = [socket.socket() for _ in range(4)]
    try:
        for probe in sockets:
            probe.bind(("127.0.0.1", 0))
        return [int(probe.getsockname()[1]) for probe in sockets]
    finally:
        for probe in sockets:
            probe.close()


def runtime_environment() -> dict[str, str]:
    # Application children must not inherit provisioner/migration/admin secrets.
    allowed = {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
        "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "CI",
        "PLAYWRIGHT_BROWSERS_PATH", "UV_CACHE_DIR",
        "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432",
        "HOMEDRIVE", "HOMEPATH",
    }
    return {key: value for key, value in os.environ.items() if key.upper() in allowed}


def run(command: list[str], env: dict[str, str], timeout: int = 600) -> None:
    process = subprocess.Popen(
        command, cwd=ROOT, env=env,
        start_new_session=sys.platform != "win32",
    )
    try:
        result = process.wait(timeout=timeout)
        if result:
            raise subprocess.CalledProcessError(result, command)
    finally:
        if process.poll() is None:
            # Stop only this invocation's process tree, including browser/app workers.
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=True, capture_output=True, timeout=20,
                )
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=20)


def wait_provider(origin: str) -> None:
    deadline = time.monotonic() + 180
    with httpx.Client(timeout=2, trust_env=False) as client:
        while time.monotonic() < deadline:
            try:
                if client.get(origin + "/realms/master/.well-known/openid-configuration").status_code == 200:
                    return
            except httpx.HTTPError:
                pass  # Readiness polling only; timeout below is a hard failure.
            time.sleep(1)
    raise RuntimeError("Owned Keycloak did not become ready")


async def provision(database: IsolatedDatabase, origin: str, web: str) -> dict[str, object]:
    async with httpx.AsyncClient(timeout=5, trust_env=False) as transport:
        provider = KeycloakLocal(transport, origin)
        await provider.login()
        await provider.setup_realm()  # Refuses an existing realm.
        clients = await provider.request("GET", "/admin/realms/quezo-local/clients?clientId=quezo-web")
        if not isinstance(clients, list) or len(clients) != 1 or not isinstance(clients[0], dict):
            raise RuntimeError("Owned confidential client is missing")
        client = clients[0]
        client["redirectUris"] = [web + "/auth/callback"]
        client["webOrigins"] = [web]
        client["attributes"]["post.logout.redirect.uris"] = web
        await provider.request(
            "PUT", f"/admin/realms/quezo-local/clients/{client['id']}", payload=client, expected=204,
        )
        discovery = await transport.get(provider.issuer + "/.well-known/openid-configuration")
        if discovery.status_code != 200 or discovery.json()["issuer"] != provider.issuer:
            raise RuntimeError("Provisioned discovery issuer does not match exactly")
        result: dict[str, object] = {}
        async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
            for name, account in ACCOUNTS.items():
                password = secrets.token_urlsafe(32)
                os.environ["QUEZO_SYNTHETIC_PASSWORD"] = password
                account_id = await provision_account(db, provider, provider.issuer, name)
                result[name] = {
                    "username": account.username, "password": password,
                    "id": str(account_id), "roles": sorted(account.roles),
                }
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", action="store_true", help="Also run every existing assignment check")
    parser.add_argument("--grep", help="Run a focused Playwright test title")
    args = parser.parse_args()
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError("Node and npm are required")
    project = "quezo-i02-" + uuid4().hex[:12]
    pg_port, kc_port, web_port, api_port = unused_ports()
    origin, web = f"http://localhost:{kc_port}", f"http://127.0.0.1:{web_port}"
    env = runtime_environment()
    context = json.loads(subprocess.check_output(
        ["docker", "context", "inspect"], env=env, text=True, timeout=15,
    ))
    if not context[0]["Endpoints"]["docker"]["Host"].startswith(("npipe:", "unix:")):
        raise RuntimeError("I02 requires a local Docker engine, not a remote context")
    env.update({
        "NEXT_TELEMETRY_DISABLED": "1",
        "QUEZO_TEST_PORT": str(pg_port), "KEYCLOAK_TEST_PORT": str(kc_port),
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "KEYCLOAK_ADMIN": "quezo-admin", "KEYCLOAK_ADMIN_PASSWORD": secrets.token_urlsafe(32),
        "KEYCLOAK_LOCAL_ORIGIN": origin, "QUEZO_OIDC_CLIENT_SECRET": secrets.token_urlsafe(32),
        "QUEZO_SYNTHETIC_PASSWORD": secrets.token_urlsafe(32),
        **{f"QUEZO_TEST_{role}_PASSWORD": secrets.token_urlsafe(32)
           for role in ("ADMIN", "MIGRATION", "RUNTIME", "WEB")},
    })
    env["QUEZO_TEST_ADMIN_URL"] = (
        f"postgresql://quezo_test_admin:{env['QUEZO_TEST_ADMIN_PASSWORD']}"
        f"@127.0.0.1:{pg_port}/quezo_test_control"
    )
    # Ignore .env, ambient Compose settings and all development services.
    compose = ["docker", "compose", "--env-file", os.devnull, "-f", str(ROOT / "compose.yaml"),
               "-p", project, "--profile", "test", "--profile", "identity-test"]
    original = dict(os.environ)
    os.environ.update(env)
    print(f"I02 owned project: {project}; PostgreSQL {pg_port}; Keycloak {kc_port}; web {web_port}; API {api_port}", flush=True)
    try:
        run(compose + ["up", "-d", "--wait", "postgres-test", "keycloak-test"], env, 240)
        wait_provider(origin)
        run(["docker", "exec", project + "-postgres-test-1", "postgres", "--version"], env, 15)
        run([node, "--version"], env, 15)
        run([sys.executable, "--version"], env, 15)
        if args.checks:
            for command in (
                ["run", "typecheck"], ["test"], ["run", "build"], ["run", "api:check"],
                ["run", "test:contracts"], ["run", "test:db"], ["run", "test:identity"],
                ["run", "test:identity:integration"], ["run", "test:web:production"],
            ):
                print("CHECK: npm " + " ".join(command), flush=True)
                run([npm, *command], env)
        else:
            run([npm, "run", "build"], env)
        with isolated_database() as database:
            run_migrations(database.migration_url)
            with asyncio.Runner(loop_factory=database_loop_factory) as runner:
                accounts = runner.run(provision(database, origin, web))
            with tempfile.TemporaryDirectory(prefix="quezo-i02-results-") as results:
                browser_env = runtime_environment()
                browser_env.update({
                    "NEXT_TELEMETRY_DISABLED": "1", "I02_OWNED_PROJECT": project,
                    "I02_WEB_ORIGIN": web, "I02_API_ORIGIN": f"http://127.0.0.1:{api_port}",
                    "I02_ISSUER": origin + "/realms/quezo-local", "I02_PYTHON": sys.executable,
                    "I02_CLIENT_SECRET": env["QUEZO_OIDC_CLIENT_SECRET"],
                    "I02_ACCOUNTS": json.dumps(accounts), "I02_RESULTS": results,
                    "I02_WEB_DATABASE": database.web_url, "I02_API_DATABASE": database.runtime_url,
                })
                command = [node, str(ROOT / "node_modules" / "@playwright" / "test" / "cli.js"),
                           "test", "--config", "tests/e2e/playwright.config.ts"]
                if args.grep:
                    command += ["--grep", args.grep]
                run(command, browser_env, 900)
    finally:
        try:
            run(compose + ["rm", "-s", "-f", "postgres-test", "keycloak-test"], env, 90)
            run(["docker", "network", "rm", project + "_default"], env, 30)
        finally:
            os.environ.clear()
            os.environ.update(original)
        print("I02 owned services/network removed; no development volumes touched.", flush=True)


if __name__ == "__main__":
    main()
