import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.modules.auth.domain.value_objects.password import Password
from app.modules.auth.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


@pytest.fixture
def cheap_password_hash():
    """Argon2 at the lowest cost it accepts: the parameters are not what these tests check."""
    return PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1),))


class TestArgon2PasswordHasher:
    async def test_does_not_return_the_password(self, cheap_password_hash: PasswordHash):
        hasher = Argon2PasswordHasher(password_hash=cheap_password_hash)

        password_hash = await hasher.hash(Password("a-long-enough-password"))

        assert "a-long-enough-password" not in password_hash

    async def test_produces_a_hash_the_same_password_verifies_against(
        self, cheap_password_hash: PasswordHash
    ):
        hasher = Argon2PasswordHasher(password_hash=cheap_password_hash)

        password_hash = await hasher.hash(Password("a-long-enough-password"))

        assert cheap_password_hash.verify("a-long-enough-password", password_hash) is True
        assert cheap_password_hash.verify("another-long-password", password_hash) is False

    async def test_hashes_the_same_password_differently_every_time(
        self, cheap_password_hash: PasswordHash
    ):
        hasher = Argon2PasswordHasher(password_hash=cheap_password_hash)
        password = Password("a-long-enough-password")

        # A fresh random salt per hash: equal hashes would mean the salt is shared, and one
        # rainbow table would then cover every account.
        assert await hasher.hash(password) != await hasher.hash(password)

    async def test_encodes_the_algorithm_and_its_parameters_in_the_hash(
        self, cheap_password_hash: PasswordHash
    ):
        hasher = Argon2PasswordHasher(password_hash=cheap_password_hash)

        password_hash = await hasher.hash(Password("a-long-enough-password"))

        # What lets a hash stored under today's parameters still be verified after they change.
        assert password_hash.startswith("$argon2id$")

    async def test_defaults_to_the_recommended_hasher(self):
        # No cheap parameters here: production must not depend on a test passing them in.
        hasher = Argon2PasswordHasher()

        password_hash = await hasher.hash(Password("a-long-enough-password"))

        assert PasswordHash.recommended().verify("a-long-enough-password", password_hash) is True
