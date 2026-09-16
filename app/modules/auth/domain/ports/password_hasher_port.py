from abc import ABC, abstractmethod

from app.modules.auth.domain.value_objects.password import Password


class PasswordHasherPort(ABC):
    """Turns a plain-text password into a hash safe to store.

    The domain only needs a hash to keep; which algorithm produces it is an infrastructure choice,
    so it can change (e.g. Argon2 to bcrypt) without touching the use cases.
    """

    @abstractmethod
    async def hash(self, password: Password) -> str:
        """Hash `password` with a fresh random salt.

        Async because hashing is deliberately slow CPU work: an adapter can run it off the event
        loop so one registration does not stall every other request.

        Args:
            password: The plain-text password. Taking `Password` rather than `str` means only a
                password that passed the length rule can be hashed and stored.

        Returns:
            The encoded hash, including algorithm, parameters and salt.
        """
