import uuid

from app.modules.auth.domain.entities.user import User
from app.modules.auth.domain.exceptions.user_already_exists import UserAlreadyExistsError
from app.modules.auth.domain.ports.user_repository_port import UserRepositoryPort
from app.modules.auth.domain.value_objects.email import Email


class InMemoryUserRepository(UserRepositoryPort):
    def __init__(self):
        self._users: dict[uuid.UUID, User] = {}

    async def create_user(self, user: User) -> User:
        # Mirrors the unique index on lower(email): the email, not the id, is what collides.
        if self.get_by_email(user.email) is not None:
            raise UserAlreadyExistsError(f"User with email {user.email} already exists.")
        self._users[user.id] = user
        return user

    def get_by_email(self, email: Email) -> User | None:
        """Inspection helper, not part of the port: tests call it directly, so it stays synchronous."""
        return next((user for user in self._users.values() if user.email == email), None)
