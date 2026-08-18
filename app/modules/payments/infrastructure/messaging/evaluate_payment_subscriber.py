from app.modules.payments.application.use_cases.evaluate_payment_use_case import (
    EvaluatePaymentUseCase,
)
from app.shared.messaging.contracts.payment_verdict_message import PaymentVerdictMessage


class EvaluatePaymentSubscriber:
    def __init__(self, evaluate_payment_use_case: EvaluatePaymentUseCase):
        self.evaluate_payment_use_case = evaluate_payment_use_case

    def handle(self, message: PaymentVerdictMessage) -> None:
        self.evaluate_payment_use_case.execute(
            payment_id=message.payment_id,
            verdict=message.verdict,
        )
