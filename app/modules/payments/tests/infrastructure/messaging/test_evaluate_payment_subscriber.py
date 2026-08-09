import uuid
from decimal import Decimal

from app.modules.payments.application.use_cases.evaluate_payment_use_case import (
    EvaluatePaymentUseCase,
)
from app.modules.payments.domain.entities.payment import Payment, PaymentState
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.infrastructure.messaging.evaluate_payment_subscriber import (
    EvaluatePaymentSubscriber,
)
from app.modules.payments.infrastructure.messaging.payment_verdict_message import (
    PaymentVerdictMessage,
)
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository


class TestEvaluatePaymentSubscriber:
    def test_approved_verdict_message_transitions_payment_to_approved(self):
        payment_repository = InMemoryPaymentRepository()

        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))
        payment_repository.add(payment)

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        subscriber = EvaluatePaymentSubscriber(evaluate_payment_use_case=evaluate_payment_use_case)

        message = PaymentVerdictMessage(payment_id=payment.id, verdict="approved")
        subscriber.handle(message)

        updated_payment = payment_repository.get_payment_by_id(payment.id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.APPROVED

    def test_rejected_verdict_message_transitions_payment_to_rejected(self):
        payment_repository = InMemoryPaymentRepository()

        payment = Payment(id=uuid.uuid4(), amount=Money(Decimal("100.00"), "USD"))
        payment_repository.add(payment)

        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        subscriber = EvaluatePaymentSubscriber(evaluate_payment_use_case=evaluate_payment_use_case)

        message = PaymentVerdictMessage(payment_id=payment.id, verdict="rejected")
        subscriber.handle(message)

        updated_payment = payment_repository.get_payment_by_id(payment.id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.REJECTED
