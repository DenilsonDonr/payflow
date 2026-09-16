import asyncio

from pwdlib import PasswordHash

from app.modules.auth.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.auth.domain.value_objects.password import Password


class Argon2PasswordHasher(PasswordHasherPort):
    """Hashes passwords with Argon2id, pwdlib's recommended configuration.

    Argon2id is deliberately expensive in both time and memory, which is what makes a stolen
    `users.password_hash` slow to crack. The cost is paid on every registration and login, so it
    is real work, not a formality.

    The salt is random per hash and travels inside the encoded string, together with the algorithm
    and its parameters. That is why two hashes of the same password differ, and why a hash produced
    with older parameters can still be verified after the parameters change.
    """

    def __init__(self, password_hash: PasswordHash | None = None):
        """Create the hasher.

        Args:
            password_hash: The pwdlib hasher to use. Defaults to `PasswordHash.recommended()`,
                Argon2id with pwdlib's parameters. A test can pass a cheaper one so it does not
                spend the full cost on every case.
        """
        self._password_hash = (
            password_hash if password_hash is not None else PasswordHash.recommended()
        )

    async def hash(self, password: Password) -> str:
        """Hash `password` on a worker thread.

        pwdlib is synchronous and Argon2 burns CPU for tens of milliseconds by design. Run inline,
        it would block the event loop for that long and stall every other request; `to_thread`
        moves it off, and argon2-cffi releases the GIL while it runs.

        Args:
            password: The plain-text password to hash.

        Returns:
            The encoded Argon2 hash, including the algorithm, its parameters and the salt.
        """
        return await asyncio.to_thread(self._password_hash.hash, password.value)
