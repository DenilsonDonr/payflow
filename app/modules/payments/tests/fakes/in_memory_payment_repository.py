from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.entities.payment import Payment

class InMemoryPaymentRepository(PaymentRepositoryPort):
    def __init__(self):
        self._payments: dict[str, Payment] = {}

    def add(self, payment: Payment) -> None:
        self._payments[payment.id] = payment
    
    def create_payment(self, payment: Payment) -> Payment | None:
        self.add(payment)
        return payment
    
    def get_payment_by_id(self, payment_id: str) -> Payment | None:
        return self._payments.get(payment_id)