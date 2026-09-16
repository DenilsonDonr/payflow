from dataclasses import dataclass

# RFC 5321 caps a forward path at 256 octets, two of them the angle brackets around the address.
MAX_LENGTH = 254


@dataclass(frozen=True)
class Email:
    """An email address, normalized so two spellings of the same account compare equal.

    The address is stripped and lowercased on creation, so `Email(" Ana@X.com ")` and
    `Email("ana@x.com")` are the same value. The format check is deliberately shallow: it catches
    typos, not undeliverable addresses. Only sending a message proves an address exists.

    Attributes:
        value: The normalized address.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate and normalize `value`.

        Raises:
            TypeError: If `value` is not a string.
            ValueError: If `value` is empty, longer than 254 characters, or not shaped like
                `local@domain.tld`.
        """
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(self.value, str): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Email must be a string.")

        # Frozen dataclasses do not allow direct assignment to fields, so we use
        # object.__setattr__ to store the normalized address.
        object.__setattr__(self, 'value', self.value.strip().lower())

        if not self.value:
            raise ValueError("Email must not be empty.")
        if len(self.value) > MAX_LENGTH:
            raise ValueError(f"Email must be at most {MAX_LENGTH} characters.")

        local, separator, domain = self.value.rpartition("@")
        if not separator or not local or "@" in local:
            raise ValueError("Email must contain exactly one '@' with text before it.")
        if any(char.isspace() for char in self.value):
            raise ValueError("Email must not contain whitespace.")
        if "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Email domain must look like 'example.com'.")

    def __str__(self) -> str:
        """Return the normalized address, e.g. for SQL parameters or HTTP responses."""
        return self.value
