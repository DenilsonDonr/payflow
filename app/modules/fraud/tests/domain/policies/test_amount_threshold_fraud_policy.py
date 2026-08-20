from decimal import Decimal

import pytest

from app.modules.fraud.domain.policies.amount_threshold_fraud_policy import (
    AmountThresholdFraudPolicy,
)


class TestAmountThresholdFraudPolicy:
    @pytest.mark.parametrize(
        ("amount", "expected"),
        [
            (Decimal("1000.01"), True),
            (Decimal("10000.00"), True),
            (Decimal("1000.00"), False),
            (Decimal("999.99"), False),
            (Decimal("0.00"), False),
        ],
    )
    def test_is_suspicious(self, amount: Decimal, expected: bool):
        policy = AmountThresholdFraudPolicy()

        result = policy.is_suspicious(amount=amount)

        assert result is expected
