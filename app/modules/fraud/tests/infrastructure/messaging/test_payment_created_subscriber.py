import uuid
from decimal import Decimal

from app.modules.fraud.infrastructure.messaging.payment_created_subscriber import (
    PaymentCreatedSubscriber,
)
from app.modules.fraud.tests.fakes.fake_evaluate_fraud_use_case import (
    FakeEvaluateFraudUseCase,
)
from app.modules.fraud.tests.fakes.fake_payment_verdict_publisher import (
    FakePaymentVerdictPublisher,
)
from app.shared.messaging.contracts.payment_created_message import PaymentCreatedMessage


class TestPaymentCreatedSubscriber:
    def test_handle_publishes_rejected_verdict_when_amount_is_suspicious(self):
        evaluate_fraud_use_case = FakeEvaluateFraudUseCase(is_suspicious=True)
        payment_verdict_publisher = FakePaymentVerdictPublisher()
        subscriber = PaymentCreatedSubscriber(
            evaluate_fraud_use_case=evaluate_fraud_use_case,
            payment_verdict_publisher=payment_verdict_publisher,
        )

        message = PaymentCreatedMessage(
            payment_id=uuid.uuid4(),
            amount=Decimal("1500.00"),
            currency="USD",
        )
        subscriber.handle(message)

        assert evaluate_fraud_use_case.amount_called_with == message.amount
        assert payment_verdict_publisher.payment_id_called_with == message.payment_id
        assert payment_verdict_publisher.verdict_called_with == "rejected"

    def test_handle_publishes_approved_verdict_when_amount_is_not_suspicious(self):
        evaluate_fraud_use_case = FakeEvaluateFraudUseCase(is_suspicious=False)
        payment_verdict_publisher = FakePaymentVerdictPublisher()
        subscriber = PaymentCreatedSubscriber(
            evaluate_fraud_use_case=evaluate_fraud_use_case,
            payment_verdict_publisher=payment_verdict_publisher,
        )

        message = PaymentCreatedMessage(
            payment_id=uuid.uuid4(),
            amount=Decimal("100.00"),
            currency="USD",
        )
        subscriber.handle(message)

        assert evaluate_fraud_use_case.amount_called_with == message.amount
        assert payment_verdict_publisher.payment_id_called_with == message.payment_id
        assert payment_verdict_publisher.verdict_called_with == "approved"
