import uuid
from decimal import Decimal

import pytest

from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.application.use_cases.evaluate_payment_use_case import EvaluatePaymentUseCase
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository


class TestPaymentEvaluate:
    def test_approved_verdict_transitions_payment_to_approved(self):
        payment_repository = InMemoryPaymentRepository()

        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))
        payment_repository.add(payment)

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        evaluate_payment_use_case.execute(payment_id=payment.id, verdict="approved")

        updated_payment = payment_repository.get_payment_by_id(payment.id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.APPROVED

    def test_rejected_verdict_transitions_payment_to_rejected(self):
        payment_repository = InMemoryPaymentRepository()

        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))
        payment_repository.add(payment)

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        evaluate_payment_use_case.execute(payment_id=payment.id, verdict="rejected")

        updated_payment = payment_repository.get_payment_by_id(payment.id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.REJECTED

    def test_invalid_verdict_raises_exception(self):
        payment_repository = InMemoryPaymentRepository()

        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))
        payment_repository.add(payment)

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)

        with pytest.raises(ValueError, match="Invalid verdict"):
            evaluate_payment_use_case.execute(payment_id=payment.id, verdict="invalid_verdict")

    def test_payment_not_found_raises_exception(self):
        payment_repository = InMemoryPaymentRepository()

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)

        with pytest.raises(ValueError, match="Payment with ID .* not found."):
            evaluate_payment_use_case.execute(payment_id=uuid.uuid4(), verdict="approved")
