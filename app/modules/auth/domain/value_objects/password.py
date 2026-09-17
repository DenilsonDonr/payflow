from dataclasses import dataclass, field

# NIST SP 800-63B: at least 15 characters when the password is the only authentication factor.
MIN_LENGTH = 15
# NIST SP 800-63B: allow at least 64, so long passphrases fit.
MAX_LENGTH = 64


@dataclass(frozen=True)
class Password:
    """A plain-text password that satisfies the length rule, on its way to being hashed.

    Only length is checked. Composition rules (an uppercase, a digit, a symbol) are left out on
    purpose: they push people toward predictable choices like "Password1!" without making
    passwords harder to guess.

    The value is kept exactly as typed, spaces included, because any change would make the same
    password stop matching its hash.

    Attributes:
        value: The plain-text password. Hidden from `repr` and `str`.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        """Validate the length of `value`.

        Raises:
            TypeError: If `value` is not a string.
            ValueError: If `value` is shorter than 15 or longer than 64 characters.
        """
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(self.value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Password must be a string.")

        if len(self.value) < MIN_LENGTH:
            raise ValueError(f"Password must be at least {MIN_LENGTH} characters.")
        if len(self.value) > MAX_LENGTH:
            raise ValueError(f"Password must be at most {MAX_LENGTH} characters.")
