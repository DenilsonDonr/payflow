import uuid

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort


class InMemoryPaymentRepository(PaymentRepositoryPort):
    def __init__(self):
        self._payments: dict[uuid.UUID, Payment] = {}

    def add(self, payment: Payment) -> None:
        """Seeding helper, not part of the port: tests call it directly, so it stays synchronous."""
        self._payments[payment.id] = payment

    async def create_payment(self, payment: Payment) -> Payment:
        self.add(payment)
        return payment

    async def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return self._payments.get(payment_id)

    async def update_payment(self, payment: Payment) -> None:
        if payment.id in self._payments:
            self._payments[payment.id] = payment
