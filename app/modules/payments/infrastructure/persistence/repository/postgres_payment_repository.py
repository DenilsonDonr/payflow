import uuid

import psycopg
from psycopg.types.json import Jsonb

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.value_objects.money import Money
from app.shared.persistence.postgres_connection import ConnectionDB


class PostgresPaymentRepository(PaymentRepositoryPort):
    """Every method borrows a connection for its own transaction and gives it back.

    Leaving the `async with` commits, or rolls back if the block raised, so neither is written here.
    """

    def __init__(self, connection: ConnectionDB):
        self.connection = connection

    async def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        async with self.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "SELECT id, user_id, amount, currency, state FROM payments WHERE id = %s",
                (payment_id,),
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            row_id, user_id, amount, currency, state = row

            return Payment.reconstitute(
                id=row_id,
                user_id=user_id,
                amount=Money(amount=amount, currency=currency),
                state=PaymentState(state),
            )

    async def create_payment(self, payment: Payment) -> Payment:
        try:
            async with self.connection.connection() as conn, conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO payments (id, user_id, amount, currency, state)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (
                        payment.id,
                        payment.user_id,
                        payment.amount.amount,
                        payment.amount.currency,
                        payment.state.value,
                    ),
                )

                # Drained inside the transaction so the rows commit or roll back with the payment.
                # Tradeoff: pull_events() empties the entity and a rollback does not restore it.
                # Harmless today, as the use case neither retries nor reuses the payment on error.
                for event in payment.pull_events():
                    await cursor.execute(
                        "INSERT INTO outbox"
                        " (event_id, aggregate_type, aggregate_id, event_type, payload)"
                        " VALUES (%s, %s, %s, %s, %s)",
                        (
                            event.event_id,
                            event.aggregate_type,
                            event.aggregate_id,
                            event.event_type,
                            Jsonb(event.payload()),
                        ),
                    )

                return payment
        except psycopg.IntegrityError as e:
            # Only the payments PK means "already exists"; an outbox unique violation is also 23505.
            if e.sqlstate == "23505" and e.diag.constraint_name == "payments_pkey":
                raise PaymentAlreadyExistsError(
                    f"Payment with ID {payment.id} already exists."
                ) from e
            raise

    async def update_payment(self, payment: Payment) -> None:
        async with self.connection.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE payments SET state = %s WHERE id = %s",
                (payment.state.value, payment.id),
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Payment with ID {payment.id} not found.")
