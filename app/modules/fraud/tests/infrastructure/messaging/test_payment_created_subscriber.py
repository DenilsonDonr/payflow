import uuid
from decimal import Decimal

from app.modules.fraud.infrastructure.messaging.payment_created_subscriber import (
    PaymentCreatedSubscriber,
)
from app.modules.fraud.tests.fakes.fake_evaluate_fraud_use_case import (
    FakeEvaluateFraudUseCase,
)
from app.shared.messaging.contracts.payment_created_message import PaymentCreatedMessage


class TestPaymentCreatedSubscriber:
    def test_handle_calls_evaluate_fraud_use_case_with_message_amount(self):
        evaluate_fraud_use_case = FakeEvaluateFraudUseCase()
        subscriber = PaymentCreatedSubscriber(
            evaluate_fraud_use_case=evaluate_fraud_use_case
        )

        message = PaymentCreatedMessage(
            payment_id=uuid.uuid4(),
            amount=Decimal("1500.00"),
            currency="USD",
        )
        subscriber.handle(message)

        assert evaluate_fraud_use_case.amount_called_with == message.amount
