import uuid

from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.entities.payment import Payment

class GetPaymentUseCase:
    def __init__(self, payment_repository_port: PaymentRepositoryPort):
        self.payment_repository_port = payment_repository_port

    def execute(self, payment_id: uuid.UUID) -> Payment | None:
        return self.payment_repository_port.get_payment_by_id(payment_id)