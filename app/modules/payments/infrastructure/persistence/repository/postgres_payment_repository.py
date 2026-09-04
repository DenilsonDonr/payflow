import uuid

import psycopg

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB


class PostgresPaymentRepository(PaymentRepositoryPort):
    """Every method borrows a connection for its own transaction and gives it back.

    Leaving the `async with` commits, or rolls back if the block raised, so neither is written here.
    """

    def __init__(self, connection: ConnectionDB):
        self.connection = connection

    async def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        async with self.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, amount, currency, state FROM payments WHERE id = %s",
                (str(payment_id),)
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            row_id, amount, currency, state = row

            return Payment.reconstitute(
                id=uuid.UUID(row_id),
                amount=Money(amount=amount, currency=currency),
                state=PaymentState(state)
            )

    async def create_payment(self, payment: Payment) -> Payment:
        try:
            async with self.connection.connection() as conn, conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO payments (id, amount, currency, state) VALUES (%s, %s, %s, %s)",
                    (
                        payment.id,
                        payment.amount.amount,
                        payment.amount.currency,
                        payment.state.value,
                    ),
                )

                return payment
        except psycopg.IntegrityError as e:
            if e.sqlstate == '23505':  # Unique violation error code
                raise PaymentAlreadyExistsError(
                    f"Payment with ID {payment.id} already exists."
                ) from e
            raise

    async def update_payment(self, payment: Payment) -> None:
        async with self.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE payments SET state = %s WHERE id = %s",
                (payment.state.value, str(payment.id))
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Payment with ID {payment.id} not found.")
