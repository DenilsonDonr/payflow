from abc import ABC, abstractmethod
import uuid
from app.modules.payments.domain.entities.payment import Payment

class PaymentRepositoryPort(ABC):
    @abstractmethod
    def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        pass

    @abstractmethod
    def create_payment(self, payment: Payment) -> Payment | None:
        pass