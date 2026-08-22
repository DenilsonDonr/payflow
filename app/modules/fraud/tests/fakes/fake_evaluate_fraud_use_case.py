from decimal import Decimal

from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import (
    EvaluateFraudUseCase,
)
from app.modules.fraud.domain.policies.amount_threshold_fraud_policy import (
    AmountThresholdFraudPolicy,
)


class FakeEvaluateFraudUseCase(EvaluateFraudUseCase):
    def __init__(self) -> None:
        super().__init__(fraud_policy_port=AmountThresholdFraudPolicy())
        self.amount_called_with: Decimal | None = None

    def execute(self, amount: Decimal) -> bool:
        self.amount_called_with = amount
        return True
