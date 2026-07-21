from decimal import Decimal

import pytest

from app.modules.payments.domain.value_objects.money import Money


class TestMoney:
    def test_create_valid_values(self):
        money = Money(amount=Decimal("100.00"), currency="USD")
        assert money.amount == Decimal("100.00")
        assert money.currency == "USD"

    def test_verify_negative_amount(self):
        with pytest.raises(ValueError, match="greater than zero"):
            Money(amount=Decimal("-100.00"), currency="USD")

    def test_verify_zero_amount(self):
        with pytest.raises(ValueError, match="greater than zero"):
            Money(amount=Decimal("0.00"), currency="USD")

    @pytest.mark.parametrize("currency", ["US", "USDT", "US1", "123", ""])
    def test_verify_invalid_currency_code(self, currency):
        with pytest.raises(ValueError, match="3-letter ISO 4217 code"):
            Money(amount=Decimal("100.00"), currency=currency)

    def test_currency_uppercase(self):
        money = Money(amount=Decimal("100.00"), currency="usd")
        assert money.currency == "USD"

    @pytest.mark.parametrize("amount", [100.00, 100, "100.00", None, True])
    def test_amount_rejects_non_decimal(self, amount):
        with pytest.raises(TypeError, match="Amount must be a Decimal instance"):
            Money(amount=amount, currency="USD")  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("currency", [123, None, b"USD"])
    def test_currency_rejects_non_string(self, currency):
        with pytest.raises(TypeError, match="Currency must be a string"):
            Money(amount=Decimal("100.00"), currency=currency)  # pyright: ignore[reportArgumentType]

    def test_equality(self):
        money1 = Money(amount=Decimal("10.01"), currency="USD")
        money2 = Money(amount=Decimal("10.01"), currency="USD")
        assert money1 == money2

    def test_inequality(self):
        base = Money(amount=Decimal("10.01"), currency="USD")
        assert base != Money(amount=Decimal("10.02"), currency="USD")
        assert base != Money(amount=Decimal("10.01"), currency="EUR")

    def test_immutability(self):
        money = Money(amount=Decimal("100.00"), currency="USD")

        with pytest.raises(AttributeError):
            money.amount = Decimal("200.00")  # pyright: ignore[reportAttributeAccessIssue]

        with pytest.raises(AttributeError):
            money.currency = "EUR"  # pyright: ignore[reportAttributeAccessIssue]

    def test_hashable(self):
        money_set = {Money(amount=Decimal("100.00"), currency="USD")}
        assert Money(amount=Decimal("100.00"), currency="USD") in money_set
