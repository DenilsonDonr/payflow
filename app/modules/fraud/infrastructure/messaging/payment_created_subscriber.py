from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import (
    EvaluateFraudUseCase,
)
from app.shared.messaging.contracts.payment_created_message import PaymentCreatedMessage


class PaymentCreatedSubscriber:
    def __init__(self, evaluate_fraud_use_case: EvaluateFraudUseCase) -> None:
        self.evaluate_fraud_use_case = evaluate_fraud_use_case

    def handle(self, message: PaymentCreatedMessage) -> None:
        self.evaluate_fraud_use_case.execute(amount=message.amount)
