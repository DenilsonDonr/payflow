from decimal import Decimal

from app.modules.fraud.domain.ports.fraud_policy_port import FraudPolicyPort


class FakeFraudPolicy(FraudPolicyPort):
    def __init__(self, is_suspicious: bool) -> None:
        self._is_suspicious = is_suspicious

    def is_suspicious(self, amount: Decimal) -> bool:
        return self._is_suspicious
