import pytest

from app.modules.auth.application.use_cases.register_user_use_case import (
    CLIENT_ROLE_ID,
    RegisterUserUseCase,
)
from app.modules.auth.domain.exceptions.user_already_exists import UserAlreadyExistsError
from app.modules.auth.domain.value_objects.email import Email
from app.modules.auth.tests.fakes.fake_password_hasher import FakePasswordHasher
from app.modules.auth.tests.fakes.in_memory_user_repository import InMemoryUserRepository

PASSWORD = "correct horse battery"


def make_use_case(
    repository: InMemoryUserRepository | None = None,
    hasher: FakePasswordHasher | None = None,
) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        user_repository_port=repository if repository is not None else InMemoryUserRepository(),
        password_hasher_port=hasher if hasher is not None else FakePasswordHasher(),
    )


class TestRegisterUser:
    async def test_stores_the_registered_user(self):
        repository = InMemoryUserRepository()

        user = await make_use_case(repository=repository).execute(email="ana@x.com", password=PASSWORD)

        assert repository.get_by_email(Email("ana@x.com")) == user

    async def test_stores_the_hash_not_the_plain_password(self):
        user = await make_use_case().execute(email="ana@x.com", password=PASSWORD)

        assert user.password_hash == f"hashed:{PASSWORD}"

    async def test_always_assigns_the_client_role(self):
        user = await make_use_case().execute(email="ana@x.com", password=PASSWORD)

        assert user.role_id == CLIENT_ROLE_ID

    async def test_normalizes_the_email(self):
        user = await make_use_case().execute(email="  Ana@X.com ", password=PASSWORD)

        assert user.email == Email("ana@x.com")

    async def test_rejects_an_email_already_registered_in_another_case(self):
        """Duplicates are caught after normalization: "ANA@x.com" collides with "ana@x.com"."""
        use_case = make_use_case()
        await use_case.execute(email="ana@x.com", password=PASSWORD)

        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(email="ANA@x.com", password="another long password")

    @pytest.mark.parametrize(
        ("email", "password"),
        [("not-an-email", PASSWORD), ("ana@x.com", "too short")],
    )
    async def test_invalid_input_fails_before_hashing(self, email: str, password: str):
        """Hashing is slow on purpose; a malformed email or a short password must not pay for it."""
        hasher = FakePasswordHasher()

        with pytest.raises(ValueError):
            await make_use_case(hasher=hasher).execute(email=email, password=password)

        assert hasher.calls == 0
