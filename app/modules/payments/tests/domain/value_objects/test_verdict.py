import pytest

from app.modules.payments.domain.exceptions.invalid_verdict import InvalidVerdictError
from app.modules.payments.domain.value_objects.verdict import Verdict


class TestVerdict:
    def test_verdict_approved(self):
        verdict = Verdict("approved")
        assert verdict == Verdict.APPROVED

    def test_verdict_rejected(self):
        verdict = Verdict("rejected")
        assert verdict == Verdict.REJECTED

    def test_verdict_case_insensitive(self):
        verdict = Verdict("ApPrOvEd")
        assert verdict == Verdict.APPROVED

    def test_verdict_invalid_value(self):
        with pytest.raises(InvalidVerdictError, match="Invalid verdict value"):
            Verdict("invalid_value")

    @pytest.mark.parametrize("value", [123, None, b"approved"])
    def test_verdict_non_string(self, value: object):
        with pytest.raises(TypeError, match="Verdict must be a string"):
            Verdict(value)
