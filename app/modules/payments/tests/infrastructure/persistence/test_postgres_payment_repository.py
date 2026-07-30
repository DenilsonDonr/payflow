from decimal import Decimal
import uuid

import pytest

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import PostgresPaymentRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def payment_repository():
    db_connection = ConnectionDB()
    fixed_id = uuid.uuid4()

    try:
        db_connection.connect()
    except Exception:
        pytest.skip("PostgreSQL server is not available. From the project root, run 'docker compose -f docker/development/compose.dev.yaml up -d' to start it, then re-run these integration tests.")

    repo = PostgresPaymentRepository(connection=db_connection)

    yield repo, fixed_id

    # Tear down: delete the test payment record if it exists
    conn = db_connection.get_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM payments WHERE id = %s", (str(fixed_id),))
        conn.commit()

    db_connection.close()


class TestPostgresPaymentRepository:
    def test_create_payment_raises_when_id_already_exists(self, payment_repository: tuple[PostgresPaymentRepository, uuid.UUID]):
        repo, fixed_id = payment_repository
        repo.create_payment(payment=Payment(id=fixed_id, amount=Money(amount=Decimal("100.00"), currency="USD")))
        with pytest.raises(PaymentAlreadyExistsError):
            repo.create_payment(payment=Payment(id=fixed_id, amount=Money(amount=Decimal("100.00"), currency="USD")))
