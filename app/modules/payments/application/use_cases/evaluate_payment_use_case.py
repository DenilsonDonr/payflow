import uuid
from typing import Callable

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.value_objects.verdict import Verdict

class EvaluatePaymentUseCase:
    def __init__(self, payment_repository_port: PaymentRepositoryPort):
        self.payment_repository_port = payment_repository_port

        self.verdict_actions: dict[Verdict, Callable[[Payment], None]] = {
            Verdict.APPROVED: Payment.approve,
            Verdict.REJECTED: Payment.reject,
        }

    def execute(self, payment_id: uuid.UUID, verdict: str):
        parsed_verdict = Verdict(verdict)

        payment = self.payment_repository_port.get_payment_by_id(payment_id)
        if payment is None:
            raise ValueError(f"Payment with ID {payment_id} not found.")

        self.verdict_actions[parsed_verdict](payment)

        self.payment_repository_port.update_payment(payment)
