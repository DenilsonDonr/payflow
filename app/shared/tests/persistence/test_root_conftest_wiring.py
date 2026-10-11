import os
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

from app.shared.persistence.postgres_connection import CONNINFO

ROOT = Path(__file__).resolve().parents[4]


def _run(
    code: str, *, cwd: Path, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **env_overrides}
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


class TestRootConftestWiring:
    def test_env_test_overrides_variables_exported_in_the_shell(self) -> None:
        result = _run(
            "import conftest, os; print(os.environ['POSTGRES_DB'], os.environ['POSTGRES_PORT'])",
            cwd=ROOT,
            env_overrides={"POSTGRES_DB": "payflow_db", "POSTGRES_PORT": "5432"},
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.split() == ["payflow_db_test", "5433"]

    def test_import_aborts_when_env_test_is_missing(self, tmp_path: Path) -> None:
        shutil.copy(ROOT / "conftest.py", tmp_path / "conftest.py")

        result = _run(
            "import conftest",
            cwd=tmp_path,
            env_overrides={"PYTHONPATH": str(ROOT), "POSTGRES_DB": "payflow_db"},
        )

        assert result.returncode != 0
        assert "Refusing to run the test suite" in result.stderr


@pytest.mark.integration
class TestMigrationFixture:
    def test_session_stops_when_a_reachable_database_fails_to_migrate(self) -> None:
        # With the database down the fixture only warns, so this behaviour cannot be observed.
        try:
            psycopg.connect(CONNINFO, connect_timeout=2).close()
        except psycopg.OperationalError:
            pytest.skip("test database unreachable")

        # A missing config makes alembic fail before it touches the database. The nested run
        # targets one fast unit test file; the fixture must stop it before that file runs.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "app/shared/tests/persistence/test_database_guard.py",
            ],
            cwd=ROOT,
            env={**os.environ, "ALEMBIC_CONFIG": str(ROOT / "nonexistent.ini")},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        output = result.stdout + result.stderr
        assert result.returncode == 1, output
        assert "failed against a reachable test database" in output
        assert "passed" not in output
