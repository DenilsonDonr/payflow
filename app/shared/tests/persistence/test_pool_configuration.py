from typing import cast

from app.shared.persistence.postgres_connection import ConnectionDB


def test_pool_does_not_enable_autocommit():
    # The transactional outbox is atomic only because psycopg defaults to autocommit=False: the
    # payment INSERT and the outbox INSERT share one transaction that commits when the connection
    # block ends. With autocommit=True each statement commits on its own, so a crash between them
    # would persist a payment without its event, and every happy-path test would still pass.
    # Static check on purpose (no DB, no borrowed connection, so it also runs in the fast lane).
    # Do not delete: the failure it prevents is silent.
    # psycopg_pool types kwargs as a union that includes a callable; here it is a plain dict or None.
    kwargs = cast("dict[str, object] | None", ConnectionDB().pool.kwargs)
    assert not (kwargs or {}).get("autocommit", False)
