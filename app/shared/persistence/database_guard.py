_TEST_DATABASE_SUFFIX = "_test"


def require_test_database(database_name: str) -> None:
    """Refuse to continue unless the database name marks a throwaway test database.

    The outbox relay claims ANY pending row, so a suite pointed at the development database would
    publish the developer's own data. The name is the only thing every entry point shares (env var,
    `.env`, an exported shell variable), which is why the check is on it and not on the port.
    """
    if not database_name.endswith(_TEST_DATABASE_SUFFIX):
        raise RuntimeError(
            f"Refusing to run the test suite against database {database_name!r}: its name does "
            f"not end in {_TEST_DATABASE_SUFFIX!r}. Tests must never touch the development "
            "database. The database comes from .env.test at the repo root: check that the file "
            "exists and selects the throwaway test database."
        )
