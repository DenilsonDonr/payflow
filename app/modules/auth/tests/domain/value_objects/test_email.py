import dataclasses

import pytest

from app.modules.auth.domain.value_objects.email import MAX_LENGTH, Email


class TestEmailCreation:
    def test_keeps_a_valid_address(self):
        assert Email("ana@x.com").value == "ana@x.com"

    @pytest.mark.parametrize("raw", ["Ana@X.com", "  ana@x.com  ", "\tANA@X.COM\n"])
    def test_normalizes_case_and_surrounding_whitespace(self, raw: str):
        assert Email(raw).value == "ana@x.com"

    def test_spellings_of_the_same_address_are_equal(self):
        assert Email("Ana@X.com") == Email("ana@x.com")
        assert hash(Email("Ana@X.com")) == hash(Email("ana@x.com"))

    def test_str_returns_the_normalized_address(self):
        assert str(Email("Ana@X.com")) == "ana@x.com"

    def test_accepts_subdomains_and_plus_tags(self):
        assert Email("ana+payflow@mail.x.co.uk").value == "ana+payflow@mail.x.co.uk"

    def test_accepts_the_maximum_length(self):
        """Boundary: exactly 254 characters is valid; the next test checks 255 is not."""
        address = "a" * (MAX_LENGTH - len("@x.com")) + "@x.com"

        assert Email(address).value == address

    def test_is_immutable(self):
        email = Email("ana@x.com")

        with pytest.raises(dataclasses.FrozenInstanceError):
            email.value = "other@x.com"  # pyright: ignore[reportAttributeAccessIssue]


class TestEmailValidation:
    @pytest.mark.parametrize("raw", [None, 123, b"ana@x.com"])
    def test_rejects_non_string(self, raw: object):
        with pytest.raises(TypeError, match="Email must be a string"):
            Email(raw)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_rejects_empty(self, raw: str):
        with pytest.raises(ValueError, match="must not be empty"):
            Email(raw)

    def test_rejects_longer_than_maximum(self):
        address = "a" * (MAX_LENGTH - len("@x.com") + 1) + "@x.com"

        with pytest.raises(ValueError, match=f"at most {MAX_LENGTH} characters"):
            Email(address)

    @pytest.mark.parametrize("raw", ["ana.x.com", "@x.com", "ana@@x.com", "ana@b@x.com"])
    def test_rejects_without_exactly_one_at_and_a_local_part(self, raw: str):
        with pytest.raises(ValueError, match="exactly one '@'"):
            Email(raw)

    @pytest.mark.parametrize("raw", ["ana maria@x.com", "ana@x .com"])
    def test_rejects_inner_whitespace(self, raw: str):
        with pytest.raises(ValueError, match="must not contain whitespace"):
            Email(raw)

    @pytest.mark.parametrize("raw", ["ana@", "ana@localhost", "ana@.com", "ana@x.com."])
    def test_rejects_domain_without_a_dotted_name(self, raw: str):
        """ "ana@localhost" is valid by RFC but rejected on purpose: a real user never signs up
        with a host that has no public domain."""
        with pytest.raises(ValueError, match="domain must look like"):
            Email(raw)
