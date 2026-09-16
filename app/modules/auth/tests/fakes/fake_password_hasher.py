from app.modules.auth.domain.ports.password_hasher_port import PasswordHasherPort
from app.modules.auth.domain.value_objects.password import Password


class FakePasswordHasher(PasswordHasherPort):
    """Predictable stand-in for a real hasher: tests can assert on the exact stored hash."""

    def __init__(self):
        self.calls = 0

    async def hash(self, password: Password) -> str:
        self.calls += 1
        return f"hashed:{password.value}"
