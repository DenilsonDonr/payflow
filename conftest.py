import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).parent

# This file must stay free of `app` imports above the two statements below. pytest imports the
# root conftest before app/conftest.py, which imports `main` and, through it, builds CONNINFO from
# os.environ at import time. Once that string is frozen no fixture can change the target database,
# so the environment has to be correct before anything under app/ is imported.
# override=True so .env.test beats .env; variables exported in the shell are overridden too, which
# is intended: the suite must not be redirected to another database by accident.
load_dotenv(ROOT / ".env.test", override=True)
# Loaded here too (it never overrides) so that, if .env.test is missing, the guard below sees the
# database .env would select and names it in its message instead of reporting an empty string.
load_dotenv(ROOT / ".env")

from app.shared.persistence.database_guard import require_test_database  # noqa: E402

# Last line of defence if .env.test is missing or wrong: abort instead of running against dev.
require_test_database(os.environ.get("POSTGRES_DB", ""))


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database() -> None:  # pyright: ignore[reportUnusedFunction]
    """Bring the test database to head before any test runs.

    The test container keeps its data in tmpfs, so it is empty after every restart and nothing
    else would create the schema. `alembic upgrade head` is a no-op when already at head.

    A failure never fails the session: with Postgres down the unit tests must still run, and the
    integration fixtures already skip when they cannot connect. It is surfaced as a warning so a
    broken migration against a reachable database is not silent.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        warnings.warn("alembic upgrade head timed out; integration tests may skip", stacklevel=1)
        return
    if result.returncode != 0:
        last_line = (result.stderr.strip().splitlines() or ["no output"])[-1]
        warnings.warn(f"alembic upgrade head failed (is db-test up?): {last_line}", stacklevel=1)
