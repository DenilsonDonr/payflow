from abc import ABC, abstractmethod
from decimal import Decimal


class FraudPolicyPort(ABC):

    @abstractmethod
    def is_suspicious(self, amount: Decimal) -> bool:
        pass
