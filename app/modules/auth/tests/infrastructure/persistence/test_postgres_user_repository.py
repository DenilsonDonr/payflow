import uuid

import psycopg
import pytest
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.modules.auth.domain.entities.user import User
from app.modules.auth.domain.exceptions.user_already_exists import UserAlreadyExistsError
from app.modules.auth.domain.value_objects.email import Email
from app.modules.auth.infrastructure.persistence.repository.postgres_user_repository import (
    PostgresUserRepository,
)
from app.shared.persistence.postgres_connection import CONNINFO, ConnectionDB

pytestmark = pytest.mark.integration

# Seeded by migration eb638f1f9107; users.role_id is a foreign key, so it must exist.
CLIENT_ROLE_ID = 1


def a_user(email: str, id: uuid.UUID | None = None) -> User:
    return User(
        id=id if id is not None else uuid.uuid4(),
        email=Email(email),
        password_hash="$argon2id$not-a-real-hash",
        role_id=CLIENT_ROLE_ID,
    )


@pytest.fixture
async def user_repository():
    # A pool of its own rather than the process-wide one: it belongs to this test's event
    # loop, which pytest-asyncio replaces between tests.
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
        CONNINFO, min_size=1, max_size=2, open=False
    )
    db_connection = ConnectionDB(pool=pool)
    # Unique per test run, so a leftover row from an interrupted run cannot fail the next one.
    email = f"{uuid.uuid4()}@example.com"

    try:
        await pool.open(wait=True, timeout=3)
    except PoolTimeout:
        await pool.close()
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    yield PostgresUserRepository(connection=db_connection), email

    # Tear down: LIKE, not equality, so the variants a test derives from this address go too.
    async with db_connection.connection() as conn, conn.cursor() as cursor:
        await cursor.execute("DELETE FROM users WHERE lower(email) LIKE %s", (f"%{email}",))

    await pool.close()


class TestPostgresUserRepository:
    async def test_create_user_persists_every_field(self, user_repository: tuple[PostgresUserRepository, str]):
        repo, email = user_repository
        user = a_user(email)

        returned_user = await repo.create_user(user)

        assert returned_user == user
        async with repo.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, email, password_hash, role_id FROM users WHERE email = %s", (email,)
            )
            assert await cursor.fetchone() == (
                user.id,
                email,
                user.password_hash,
                CLIENT_ROLE_ID,
            )

    async def test_create_user_raises_when_the_email_is_already_registered(self, user_repository: tuple[PostgresUserRepository, str]):
        repo, email = user_repository
        await repo.create_user(a_user(email))

        # A different id, the same address: the email is what collides, not the identifier.
        with pytest.raises(UserAlreadyExistsError):
            await repo.create_user(a_user(email))

    async def test_create_user_raises_when_the_stored_email_differs_only_in_case(self, user_repository: tuple[PostgresUserRepository, str]):
        repo, email = user_repository

        # Written past Email on purpose: the value object lowercases, so going through it could
        # never produce a row in mixed case. What is under test is the index on lower(email),
        # which is what still protects the account if a row is ever written without the VO.
        async with repo.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO users (id, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
                (uuid.uuid4(), email.upper(), "$argon2id$not-a-real-hash", CLIENT_ROLE_ID),
            )

        with pytest.raises(UserAlreadyExistsError):
            await repo.create_user(a_user(email))

    async def test_create_user_does_not_report_a_duplicate_id_as_a_taken_email(self, user_repository: tuple[PostgresUserRepository, str]):
        repo, email = user_repository
        user = await repo.create_user(a_user(email))

        # Same id, a free email. A uuid4 collision is a bug in the caller, not a registration
        # someone lost, so it must surface as the integrity error it is.
        with pytest.raises(psycopg.errors.UniqueViolation):
            await repo.create_user(a_user(f"other-{email}", id=user.id))
