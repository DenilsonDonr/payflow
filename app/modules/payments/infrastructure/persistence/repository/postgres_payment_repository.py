import uuid

import psycopg

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB

class PostgresPaymentRepository(PaymentRepositoryPort):
    def __init__(self, connection: ConnectionDB):
        self.connection = connection

    def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        conn = self.connection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, amount, currency FROM payments WHERE id = %s",
                    (str(payment_id),)
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                row_id, amount, currency = row

                return Payment(
                    id=uuid.UUID(row_id),
                    amount=Money(amount=amount, currency=currency)
                )
        except Exception:
            conn.rollback()
            raise

    def create_payment(self, payment: Payment) -> Payment:
        conn = self.connection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO payments (id, amount, currency, state) VALUES (%s, %s, %s, %s)",
                    (payment.id, payment.amount.amount, payment.amount.currency, payment.state.value)
                )

                conn.commit()

                return payment
        except psycopg.IntegrityError as e:
            conn.rollback()
            if e.sqlstate == '23505':  # Unique violation error code
                raise PaymentAlreadyExistsError(f"Payment with ID {payment.id} already exists.") from e
            raise
        except Exception:
            conn.rollback()
            raise
