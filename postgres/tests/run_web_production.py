"""Built-Next HTTP check, using F01's isolated database lifecycle (no browser)."""

import os
from pathlib import Path
import subprocess

from db_helpers import isolated_database, run_migrations


def main() -> None:
    with isolated_database() as database:
        run_migrations(database.migration_url)
        result = subprocess.run(
            ["node", "--conditions=react-server", "--import", "tsx", "--test",
             "frontend/quezo/tests/production.test.ts"],
            cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "QUEZO_WEB_TEST_URL": database.web_url},
            timeout=90, check=False,
        )
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
