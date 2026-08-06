from enum import Enum

from app.modules.payments.domain.exceptions.invalid_verdict import InvalidVerdictError


class Verdict(Enum):
    APPROVED = 'approved'
    REJECTED = 'rejected'

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            raise TypeError("Verdict must be a string.")

        value = value.lower()

        for member in cls:
            if member.value == value:
                return member

        raise InvalidVerdictError(
            f"Invalid verdict value: {value}. Valid values are: {[member.value for member in cls]}"
        )
