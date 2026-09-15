import dataclasses

import pytest

from app.modules.auth.domain.value_objects.password import MAX_LENGTH, MIN_LENGTH, Password

PLAIN = "correct horse battery"


class TestPasswordCreation:
    def test_keeps_a_valid_password(self):
        assert Password(PLAIN).value == PLAIN

    def test_keeps_the_value_exactly_as_typed(self):
        """No strip or lowercase: changing the value would make it stop matching its hash."""
        raw = "  Correct Horse Battery  "

        assert Password(raw).value == raw

    @pytest.mark.parametrize("length", [MIN_LENGTH, MAX_LENGTH])
    def test_accepts_the_length_boundaries(self, length: int):
        assert Password("a" * length).value == "a" * length

    def test_accepts_without_uppercase_digits_or_symbols(self):
        assert Password("a" * MIN_LENGTH).value == "a" * MIN_LENGTH

    def test_repr_and_str_do_not_expose_the_value(self):
        """repr and str are what logs and tracebacks print."""
        password = Password(PLAIN)

        assert PLAIN not in repr(password)
        assert PLAIN not in str(password)

    def test_is_immutable(self):
        password = Password(PLAIN)

        with pytest.raises(dataclasses.FrozenInstanceError):
            password.value = "another long password"  # pyright: ignore[reportAttributeAccessIssue]


class TestPasswordValidation:
    @pytest.mark.parametrize("raw", [None, 123456789012345, b"correct horse battery"])
    def test_rejects_non_string(self, raw: object):
        with pytest.raises(TypeError, match="Password must be a string"):
            Password(raw)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("raw", ["", "a" * (MIN_LENGTH - 1)])
    def test_rejects_shorter_than_minimum(self, raw: str):
        with pytest.raises(ValueError, match=f"at least {MIN_LENGTH} characters"):
            Password(raw)

    def test_rejects_longer_than_maximum(self):
        with pytest.raises(ValueError, match=f"at most {MAX_LENGTH} characters"):
            Password("a" * (MAX_LENGTH + 1))
