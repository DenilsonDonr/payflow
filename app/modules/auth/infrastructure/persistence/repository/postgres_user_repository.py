import psycopg

from app.modules.auth.domain.entities.user import User
from app.modules.auth.domain.exceptions.user_already_exists import UserAlreadyExistsError
from app.modules.auth.domain.ports.user_repository_port import UserRepositoryPort
from app.shared.persistence.postgres_connection import ConnectionDB

# The unique index on lower(email) created by migration eb638f1f9107.
EMAIL_UNIQUE_INDEX = "ix_users_email_lower"


class PostgresUserRepository(UserRepositoryPort):
    """Every method borrows a connection for its own transaction and gives it back.

    Leaving the `async with` commits, or rolls back if the block raised, so neither is written here.
    """

    def __init__(self, connection: ConnectionDB):
        """Create the repository.

        Args:
            connection: Where it borrows connections from.
        """
        self.connection = connection

    async def create_user(self, user: User) -> User:
        """Insert the user, letting the unique index decide whether the email was taken.

        No SELECT first: between reading and writing, another registration can insert the same
        email, and only the index sees both.

        Args:
            user: The user to store. The email is written already normalized by `Email`.

        Returns:
            The stored user, unchanged: the database assigns nothing.

        Raises:
            UserAlreadyExistsError: If the email is already registered.
        """
        try:
            async with self.connection.connection() as conn, conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO users (id, email, password_hash, role_id) "
                    "VALUES (%s, %s, %s, %s)",
                    (user.id, user.email.value, user.password_hash, user.role_id),
                )

                return user
        except psycopg.errors.UniqueViolation as e:
            # The primary key can raise the same error, and a uuid4 collision is a bug, not a
            # taken email; only the index on the email may be reported as one.
            if e.diag.constraint_name == EMAIL_UNIQUE_INDEX:
                raise UserAlreadyExistsError(
                    f"User with email {user.email.value} already exists."
                ) from e
            raise
