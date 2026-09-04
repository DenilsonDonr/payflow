import uuid
from abc import ABC, abstractmethod

from app.modules.payments.domain.entities.payment import Payment


class PaymentRepositoryPort(ABC):
    @abstractmethod
    async def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        pass

    @abstractmethod
    async def create_payment(self, payment: Payment) -> Payment:
        pass

    @abstractmethod
    async def update_payment(self, payment: Payment) -> None:
        pass
