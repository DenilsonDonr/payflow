from decimal import Decimal

from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import (
    EvaluateFraudUseCase,
)
from app.modules.fraud.tests.fakes.fake_fraud_policy import FakeFraudPolicy


class TestEvaluateFraudUseCase:
    def test_execute_returns_true_when_policy_flags_amount_as_suspicious(self) -> None:
        evaluate_fraud_use_case = EvaluateFraudUseCase(
            fraud_policy_port=FakeFraudPolicy(is_suspicious=True)
        )

        result = evaluate_fraud_use_case.execute(amount=Decimal("1000.00"))

        assert result is True

    def test_execute_returns_false_when_policy_does_not_flag_amount_as_suspicious(self) -> None:
        evaluate_fraud_use_case = EvaluateFraudUseCase(
            fraud_policy_port=FakeFraudPolicy(is_suspicious=False)
        )

        result = evaluate_fraud_use_case.execute(amount=Decimal("1000.00"))

        assert result is False
