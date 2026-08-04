import uuid
from typing import Callable

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort

class EvaluatePaymentUseCase:
    def __init__(self, payment_repository_port: PaymentRepositoryPort):
        self.payment_repository_port = payment_repository_port

        self.verdict_actions: dict[str, Callable[[Payment], None]] = {
            "approved": Payment.approve,
            "rejected": Payment.reject,
        }

    def execute(self, payment_id: uuid.UUID, verdict: str):
        if verdict not in self.verdict_actions:
            raise ValueError(f"Invalid verdict: {verdict}")

        payment = self.payment_repository_port.get_payment_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment with ID {payment_id} not found.")

        self.verdict_actions[verdict](payment)

        self.payment_repository_port.update_payment(payment)
