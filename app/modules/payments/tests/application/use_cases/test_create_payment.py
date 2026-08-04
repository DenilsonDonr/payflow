from decimal import Decimal
import uuid

import pytest

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository
from app.modules.payments.application.use_cases.create_payment_use_case import CreatePaymentUseCase

class FailingPaymentRepository(PaymentRepositoryPort):
    def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return None

    def create_payment(self, payment: Payment) -> Payment:
        raise RuntimeError("Simulated persistence failure.")

    def update_payment(self, payment: Payment) -> None:
        raise NotImplementedError("This test double does not support update_payment.")

class TestPaymentCreate:
    def test_returns_payment_when_creation_succeeds(self):
        payment_repository = InMemoryPaymentRepository()

        create_payment_use_case = CreatePaymentUseCase(payment_repository_port=payment_repository)

        # Save a new payment using the use case
        payment = create_payment_use_case.execute(amount=Decimal("100.00"), currency="USD")

        # verify that the payment was created and returned
        assert payment is not None
        assert payment.id is not None

        # Get payment from the repository to verify it was saved
        saved_payment = payment_repository.get_payment_by_id(payment.id)

        # verify that the saved payment matches the created payment
        assert saved_payment is not None
        assert saved_payment == payment

    def test_raises_when_persistence_fails(self):
        payment_repository = FailingPaymentRepository()

        create_payment_use_case = CreatePaymentUseCase(payment_repository_port=payment_repository)

        # The use case must propagate the repository's error, not swallow it
        with pytest.raises(RuntimeError):
            create_payment_use_case.execute(amount=Decimal("100.00"), currency="USD")
