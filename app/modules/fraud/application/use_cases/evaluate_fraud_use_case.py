
from decimal import Decimal

from app.modules.fraud.domain.ports.fraud_policy_port import FraudPolicyPort


class EvaluateFraudUseCase:
    def __init__(self, fraud_policy_port: FraudPolicyPort) -> None:
        self.fraud_policy_port = fraud_policy_port

    def execute(self, amount: Decimal) -> bool:
        return self.fraud_policy_port.is_suspicious(amount=amount)
