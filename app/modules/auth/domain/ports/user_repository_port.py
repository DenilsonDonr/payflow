from abc import ABC, abstractmethod

from app.modules.auth.domain.entities.user import User


class UserRepositoryPort(ABC):
    """Persistence for users."""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Store a new user.

        Uniqueness of the email is enforced here, at write time, not by reading first: two
        registrations with the same email can race, and only the store can decide between them.

        Args:
            user: The user to store.

        Returns:
            The stored user.

        Raises:
            UserAlreadyExistsError: If a user with the same email already exists.
        """
