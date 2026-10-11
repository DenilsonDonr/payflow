import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

from app.shared.persistence.postgres_connection import CONNINFO

ROOT = Path(__file__).resolve().parents[4]
_PASSED_COUNT = re.compile(r"\b\d+ passed\b")


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


def _nested_pytest(
    target: str, *, cwd: Path, env_overrides: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
        cwd=cwd,
        env={**os.environ, **env_overrides},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _no_test_ran(output: str) -> bool:
    # pytest's own summary ("3 passed in 0.1s") is the signal; the word "passed" alone can show up
    # in a checkout path or in alembic output.
    return _PASSED_COUNT.search(output) is None


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

    def test_unreachable_database_only_warns_and_the_session_runs(self, tmp_path: Path) -> None:
        # A copy of the root conftest next to a .env.test that points at a port nobody listens on.
        shutil.copy(ROOT / "conftest.py", tmp_path / "conftest.py")
        (tmp_path / ".env.test").write_text("POSTGRES_DB=unreachable_test\nPOSTGRES_PORT=1\n")
        (tmp_path / "test_sanity.py").write_text("def test_runs():\n    assert True\n")

        result = _nested_pytest(
            "test_sanity.py", cwd=tmp_path, env_overrides={"PYTHONPATH": str(ROOT)}
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "test database unreachable" in output
        assert not _no_test_ran(output)


class TestNoTestRanSignal:
    def test_detects_pytest_summary_with_a_passed_count(self) -> None:
        assert not _no_test_ran("....\n7 passed, 1 warning in 0.02s\n")

    def test_ignores_the_word_passed_without_a_count(self) -> None:
        output = "rootdir: /home/me/passed-experiments\n!!! _pytest.outcomes.Exit: alembic failed"
        assert _no_test_ran(output)


@pytest.mark.integration
class TestMigrationFixture:
    _TARGET = "app/shared/tests/persistence/test_database_guard.py"

    @staticmethod
    def _skip_unless_database_is_reachable() -> None:
        # With the database down the fixture only warns, so these behaviours cannot be observed.
        try:
            psycopg.connect(CONNINFO, connect_timeout=2).close()
        except psycopg.OperationalError:
            pytest.skip("test database unreachable")

    def test_session_stops_when_a_reachable_database_fails_to_migrate(self) -> None:
        self._skip_unless_database_is_reachable()

        # A missing config makes alembic fail before it touches the database. The nested run
        # targets one fast unit test file; the fixture must stop it before that file runs.
        result = _nested_pytest(
            self._TARGET, cwd=ROOT, env_overrides={"ALEMBIC_CONFIG": str(ROOT / "nonexistent.ini")}
        )

        output = result.stdout + result.stderr
        assert result.returncode == 1, output
        assert "failed against a reachable test database" in output
        assert _no_test_ran(output), output

    def test_session_stops_when_the_server_rejects_the_credentials(self) -> None:
        self._skip_unless_database_is_reachable()

        # .env.test does not set the password and the root conftest loads .env without override,
        # so a value exported here wins. The server is up and says no: that is not "database down".
        result = _nested_pytest(
            self._TARGET, cwd=ROOT, env_overrides={"POSTGRES_PASSWORD": "definitely-wrong"}
        )

        output = result.stdout + result.stderr
        assert result.returncode == 1, output
        assert "answered on TCP but the connection failed" in output
        assert "password authentication failed" in output
        assert _no_test_ran(output), output
