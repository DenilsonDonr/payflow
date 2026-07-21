from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(self.amount, Decimal): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Amount must be a Decimal instance.")
        if not isinstance(self.currency, str): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Currency must be a string.")
        
        if self.amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        
        # Frozen dataclasses do not allow direct assignment to fields, so we use object.__setattr__ to modify the currency field to uppercase.
        object.__setattr__(self, 'currency', self.currency.upper())
        
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO 4217 code.")
