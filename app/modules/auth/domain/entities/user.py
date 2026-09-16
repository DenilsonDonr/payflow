import uuid

from app.modules.auth.domain.value_objects.email import Email


class User:
    """A registered account: who can authenticate, and which role authorizes them.

    Identity is the `id` alone. Two `User` objects with the same id are the same user even if the
    rest of their fields differ, e.g. one loaded before an update and one after.

    The password is never held in plain text, only its hash. Hashing and verifying belong outside
    the entity, so the domain does not depend on a hashing library.
    """

    def __init__(self, id: uuid.UUID, email: Email, password_hash: str, role_id: int):
        """Create a user.

        Args:
            id: Unique identifier, generated before persisting (the database does not assign it).
            email: The login address, already normalized by `Email`.
            password_hash: The hash of the password, as produced by the hashing adapter.
            role_id: The id of the role in the `roles` table that authorizes this user.

        Raises:
            TypeError: If any argument has the wrong type. A `bool` is rejected as `role_id`
                even though Python treats it as an `int`.
        """
        # Type hints are not enforced at runtime, so callers can pass any type.
        if not isinstance(id, uuid.UUID): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("User ID must be a UUID.")
        if not isinstance(email, Email): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("User email must be an instance of Email.")
        if not isinstance(password_hash, str): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("User password hash must be a string.")
        # bool is a subclass of int, so True would otherwise pass as role 1.
        if isinstance(role_id, bool) or not isinstance(role_id, int): # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("User role ID must be an integer.")

        self._id = id
        self._email = email
        self._password_hash = password_hash
        self._role_id = role_id

    def __eq__(self, other: object) -> bool:
        """Compare by identity: users are equal when their ids are equal."""
        if not isinstance(other, User):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        """Hash by id, consistent with `__eq__`, so users can be set members or dict keys."""
        return hash(self._id)

    def __repr__(self) -> str:
        """Describe the user for debugging, leaving the password hash out of logs and tracebacks."""
        return f"User(id={self._id!r}, email={self._email!r}, role_id={self._role_id!r})"

    @property
    def id(self) -> uuid.UUID:
        """The user's unique identifier."""
        return self._id

    @property
    def email(self) -> Email:
        """The normalized login address."""
        return self._email

    @property
    def password_hash(self) -> str:
        """The stored password hash, for the adapter that verifies a login attempt."""
        return self._password_hash

    @property
    def role_id(self) -> int:
        """The id of the role that decides what this user may do."""
        return self._role_id
