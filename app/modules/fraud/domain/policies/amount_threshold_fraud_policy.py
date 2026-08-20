
from decimal import Decimal

from app.modules.fraud.domain.ports.fraud_policy_port import FraudPolicyPort


class AmountThresholdFraudPolicy(FraudPolicyPort):
    def is_suspicious(self, amount: Decimal) -> bool:
        return amount > 1000
