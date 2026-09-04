import uuid
from decimal import Decimal

import pytest
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.infrastructure.persistence.postgres_connection import (
    CONNINFO,
    ConnectionDB,
)
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import (
    PostgresPaymentRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def payment_repository():
    # A pool of its own rather than the process-wide one: it belongs to this test's event
    # loop, which pytest-asyncio replaces between tests.
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
        CONNINFO, min_size=1, max_size=2, open=False
    )
    db_connection = ConnectionDB(pool=pool)
    fixed_id = uuid.uuid4()

    try:
        await pool.open(wait=True, timeout=3)
    except PoolTimeout:
        await pool.close()
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    repo = PostgresPaymentRepository(connection=db_connection)

    yield repo, fixed_id

    # Tear down: delete the test payment record if it exists
    async with db_connection.connection() as conn, conn.cursor() as cursor:
        await cursor.execute("DELETE FROM payments WHERE id = %s", (str(fixed_id),))

    await pool.close()


class TestPostgresPaymentRepository:
    async def test_create_payment_raises_when_id_already_exists(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        await repo.create_payment(payment=Payment(id=fixed_id, amount=Money(amount=Decimal("100.00"), currency="USD")))
        with pytest.raises(PaymentAlreadyExistsError):
            await repo.create_payment(payment=Payment(id=fixed_id, amount=Money(amount=Decimal("100.00"), currency="USD")))

    async def test_create_payment_and_retrieve_payment(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        payment = Payment(id=fixed_id, amount=Money(amount=Decimal("150.00"), currency="USD"))
        await repo.create_payment(payment=payment)

        retrieved_payment = await repo.get_payment_by_id(payment_id=fixed_id)

        assert retrieved_payment is not None
        assert retrieved_payment.id == payment.id
        assert retrieved_payment.amount.amount == payment.amount.amount
        assert retrieved_payment.amount.currency == payment.amount.currency

    async def test_get_payment_by_id_returns_none_for_nonexistent_payment(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository

        retrieved_payment = await repo.get_payment_by_id(payment_id=fixed_id)  # Using the fixed_id which has not been created in this test

        assert retrieved_payment is None

    async def test_retrieved_payment_preserves_its_persisted_state(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        payment = Payment(id=fixed_id, amount=Money(amount=Decimal("200.00"), currency="USD"))
        payment.approve()
        payment.complete()

        await repo.create_payment(payment=payment)
        retrieved_payment = await repo.get_payment_by_id(payment_id=fixed_id)

        assert retrieved_payment is not None
        assert retrieved_payment.id == payment.id
        assert retrieved_payment.amount.amount == payment.amount.amount
        assert retrieved_payment.amount.currency == payment.amount.currency
        assert retrieved_payment.state == PaymentState.COMPLETED

    async def test_update_payment_persists_the_new_state(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        payment = Payment(id=fixed_id, amount=Money(amount=Decimal("300.00"), currency="USD"))
        await repo.create_payment(payment=payment)

        assert payment.state == PaymentState.PENDING

        payment.approve()
        await repo.update_payment(payment=payment)

        retrieved_payment = await repo.get_payment_by_id(payment_id=fixed_id)

        assert retrieved_payment is not None
        assert retrieved_payment.state == PaymentState.APPROVED

    async def test_update_payment_raises_for_a_nonexistent_payment(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        payment = Payment(id=fixed_id, amount=Money(amount=Decimal("300.00"), currency="USD"))
        # The payment is never persisted, so the UPDATE would otherwise affect zero rows silently.

        with pytest.raises(ValueError, match="not found"):
            await repo.update_payment(payment=payment)
