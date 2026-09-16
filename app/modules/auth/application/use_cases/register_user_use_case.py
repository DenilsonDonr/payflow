import uuid

from app.modules.auth.domain.entities.user import User
from app.modules.auth.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.auth.domain.ports.user_repository_port import UserRepositoryPort
from app.modules.auth.domain.value_objects.email import Email
from app.modules.auth.domain.value_objects.password import Password

# Seeded as id 1 by the users and roles migration (eb638f1f9107).
CLIENT_ROLE_ID = 1


class RegisterUserUseCase:
    """Creates an account for a new user with the `client` role."""

    def __init__(
        self,
        user_repository_port: UserRepositoryPort,
        password_hasher_port: PasswordHasherPort,
    ):
        """Create the use case.

        Args:
            user_repository_port: Where the new user is stored.
            password_hasher_port: How the password is hashed before storing it.
        """
        self.user_repository_port = user_repository_port
        self.password_hasher_port = password_hasher_port

    async def execute(self, email: str, password: str) -> User:
        """Register a user.

        Email and password are validated before hashing, so bad input fails fast without paying
        for the hash. The role is always `client`: callers cannot choose it.

        Args:
            email: The login address as received; `Email` normalizes and validates it.
            password: The plain-text password; `Password` checks its length, and only its hash
                is stored.

        Returns:
            The registered user.

        Raises:
            TypeError: If `email` or `password` is not a string.
            ValueError: If `email` is not a valid address, or `password` is not 15 to 64
                characters long.
            UserAlreadyExistsError: If the email is already registered.
        """
        user_email = Email(email)
        user_password = Password(password)
        password_hash = await self.password_hasher_port.hash(user_password)
        user = User(
            id=uuid.uuid4(),
            email=user_email,
            password_hash=password_hash,
            role_id=CLIENT_ROLE_ID,
        )
        return await self.user_repository_port.create_user(user)
