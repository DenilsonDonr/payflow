import uuid
from decimal import Decimal

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.domain.value_objects.money import Money


class CreatePaymentUseCase:
    def __init__(self, payment_repository_port: PaymentRepositoryPort):
        self.payment_repository_port = payment_repository_port

    async def execute(self, amount: Decimal, currency: str) -> Payment:
        payment = Payment(id=uuid.uuid4(), amount=Money(amount=amount, currency=currency))
        return await self.payment_repository_port.create_payment(payment)
