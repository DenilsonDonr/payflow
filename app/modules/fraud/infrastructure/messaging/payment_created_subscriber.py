from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import (
    EvaluateFraudUseCase,
)
from app.modules.fraud.infrastructure.messaging.payment_verdict_publisher import (
    PaymentVerdictPublisher,
)
from app.shared.messaging.contracts.payment_created_message import PaymentCreatedMessage


class PaymentCreatedSubscriber:
    def __init__(
        self,
        evaluate_fraud_use_case: EvaluateFraudUseCase,
        payment_verdict_publisher: PaymentVerdictPublisher,
    ) -> None:
        self.evaluate_fraud_use_case = evaluate_fraud_use_case
        self.payment_verdict_publisher = payment_verdict_publisher

    def handle(self, message: PaymentCreatedMessage) -> None:
        is_suspicious = self.evaluate_fraud_use_case.execute(amount=message.amount)
        verdict = "rejected" if is_suspicious else "approved"
        self.payment_verdict_publisher.publish(
            payment_id=message.payment_id,
            verdict=verdict,
        )
