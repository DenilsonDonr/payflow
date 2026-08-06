import uuid

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort


class InMemoryPaymentRepository(PaymentRepositoryPort):
    def __init__(self):
        self._payments: dict[uuid.UUID, Payment] = {}

    def add(self, payment: Payment) -> None:
        self._payments[payment.id] = payment

    def create_payment(self, payment: Payment) -> Payment:
        self.add(payment)
        return payment

    def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return self._payments.get(payment_id)

    def update_payment(self, payment: Payment) -> None:
        if payment.id in self._payments:
            self._payments[payment.id] = payment
