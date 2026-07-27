from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.entities.payment import Payment

class CreatePaymentUseCase:
    def __init__(self, payment_repository_port: PaymentRepositoryPort):
        self.payment_repository_port = payment_repository_port

    def execute(self, payment: Payment) -> Payment | None:
        return self.payment_repository_port.create_payment(payment)