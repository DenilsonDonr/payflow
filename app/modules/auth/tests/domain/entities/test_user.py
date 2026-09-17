import uuid

import pytest

from app.modules.auth.domain.entities.user import User
from app.modules.auth.domain.value_objects.email import Email

DEFAULT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
OTHER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
DEFAULT_EMAIL = Email("ana@x.com")
PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


def make_user(id: uuid.UUID = DEFAULT_ID, email: Email = DEFAULT_EMAIL) -> User:
    return User(id=id, email=email, password_hash=PASSWORD_HASH, role_id=1)


class TestUserCreation:
    def test_creates_user_with_given_fields(self):
        user = User(id=DEFAULT_ID, email=DEFAULT_EMAIL, password_hash=PASSWORD_HASH, role_id=1)

        assert user.id == DEFAULT_ID
        assert user.email == DEFAULT_EMAIL
        assert user.password_hash == PASSWORD_HASH
        assert user.role_id == 1

    @pytest.mark.parametrize("id", [None, 123, "11111111-1111-1111-1111-111111111111"])
    def test_rejects_non_uuid_id(self, id: object):
        with pytest.raises(TypeError, match="User ID must be a UUID"):
            User(id=id, email=DEFAULT_EMAIL, password_hash=PASSWORD_HASH, role_id=1)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("email", [None, 123, "ana@x.com"])
    def test_rejects_non_email_value_object(self, email: object):
        """A valid address as a plain string is still rejected: it would skip the normalization
        `Email` applies, and "Ana@x.com" would no longer match "ana@x.com"."""
        with pytest.raises(TypeError, match="User email must be an instance of Email"):
            User(id=DEFAULT_ID, email=email, password_hash=PASSWORD_HASH, role_id=1)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("password_hash", [None, 123, b"hash"])
    def test_rejects_non_string_password_hash(self, password_hash: object):
        with pytest.raises(TypeError, match="User password hash must be a string"):
            User(id=DEFAULT_ID, email=DEFAULT_EMAIL, password_hash=password_hash, role_id=1)  # pyright: ignore[reportArgumentType]

    @pytest.mark.parametrize("role_id", [None, "1", 1.0, True])
    def test_rejects_non_integer_role_id(self, role_id: object):
        """`True` is the case that matters: `bool` subclasses `int`, so a plain isinstance check
        would accept it as role 1."""
        with pytest.raises(TypeError, match="User role ID must be an integer"):
            User(id=DEFAULT_ID, email=DEFAULT_EMAIL, password_hash=PASSWORD_HASH, role_id=role_id)  # pyright: ignore[reportArgumentType]


class TestUserIdentity:
    def test_users_with_same_id_are_equal(self):
        assert make_user(email=Email("ana@x.com")) == make_user(email=Email("other@x.com"))

    def test_users_with_different_id_are_not_equal(self):
        assert make_user(id=DEFAULT_ID) != make_user(id=OTHER_ID)

    def test_equal_users_share_hash(self):
        assert hash(make_user(email=Email("ana@x.com"))) == hash(
            make_user(email=Email("other@x.com"))
        )

    def test_repr_does_not_expose_password_hash(self):
        """repr is what logs and tracebacks print, so the hash must never appear in it."""
        assert PASSWORD_HASH not in repr(make_user())
