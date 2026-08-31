from decimal import Decimal

from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import (
    EvaluateFraudUseCase,
)


class FakeEvaluateFraudUseCase(EvaluateFraudUseCase):
    def __init__(self, is_suspicious: bool = True) -> None:
        self.is_suspicious = is_suspicious
        self.amount_called_with: Decimal | None = None

    def execute(self, amount: Decimal) -> bool:
        self.amount_called_with = amount
        return self.is_suspicious
