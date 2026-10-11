import os
import socket
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

    Three outcomes, depending on how the database answers a short probe:
    - Nothing answers (connection refused, timeout, host unreachable): only a warning. With
      Postgres down the unit tests must still run, and the integration fixtures already skip when
      they cannot connect.
    - A server answers but rejects us (bad password, unknown role or database): the session stops
      with the error. Treating it as "down" would skip every integration test and report green.
    - Reachable but `alembic upgrade head` fails or times out: the session stops with the full
      alembic output. Carrying on would run the suite against a stale or missing schema and
      report confusing failures far from the real cause.
    """
    # Imported here, not at the top: by now the environment is final, and the module reads it at
    # import time (see the ordering rule above).
    import psycopg

    from app.shared.persistence.postgres_connection import CONNINFO, host, port

    # psycopg gives no structured way to tell "nobody answered" from "the server said no": both
    # raise OperationalError with sqlstate None and only the message differs. A plain TCP connect
    # separates them without parsing text: if it succeeds a server is there, so any later psycopg
    # error is a rejection or a protocol failure, not an absent database.
    try:
        socket.create_connection((host, int(port)), timeout=2).close()
    except OSError as error:
        warnings.warn(
            f"test database unreachable ({error}); skipping migrations, integration tests skip",
            stacklevel=1,
        )
        return

    try:
        psycopg.connect(CONNINFO, connect_timeout=2).close()
    except psycopg.Error as error:
        pytest.exit(
            f"test database answered on TCP but the connection failed: {error}. Either the "
            "credentials are wrong or Postgres is not ready yet (start it with `up -d --wait`).",
            returncode=1,
        )

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
        pytest.exit(
            "alembic upgrade head timed out against a reachable test database", returncode=1
        )
    if result.returncode != 0:
        pytest.exit(
            "alembic upgrade head failed against a reachable test database:\n"
            # alembic prints some failures (e.g. a bad config) to stdout, so keep both streams.
            f"{result.stderr}{result.stdout}",
            returncode=1,
        )
