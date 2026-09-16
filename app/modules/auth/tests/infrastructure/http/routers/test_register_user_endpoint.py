import pytest
from fastapi.testclient import TestClient

from app.modules.auth.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.modules.auth.infrastructure.http.routers.auth_router import (
    INVALID_CREDENTIALS,
    get_register_user_use_case,
)
from app.modules.auth.tests.fakes.fake_password_hasher import FakePasswordHasher
from app.modules.auth.tests.fakes.in_memory_user_repository import InMemoryUserRepository
from main import app

client = TestClient(app)

VALID_PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def repository() -> InMemoryUserRepository:
    repository = InMemoryUserRepository()
    app.dependency_overrides[get_register_user_use_case] = lambda: RegisterUserUseCase(
        user_repository_port=repository,
        password_hasher_port=FakePasswordHasher(),
    )
    return repository


def test_register_user_endpoint(repository: InMemoryUserRepository):
    response = client.post(
        "/api/v1/auth/register", json={"email": "Ana@Example.com", "password": VALID_PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert "password_hash" not in body
    assert "password" not in body


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", VALID_PASSWORD),
        ("ana@example.com", "short"),
    ],
)
def test_register_user_endpoint_invalid_input(
    repository: InMemoryUserRepository, email: str, password: str
):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": password})

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_register_user_endpoint_taken_email_answers_like_invalid_input(
    repository: InMemoryUserRepository,
):
    data_request = {"email": "ana@example.com", "password": VALID_PASSWORD}
    client.post("/api/v1/auth/register", json=data_request)

    response = client.post("/api/v1/auth/register", json=data_request)

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_register_user_endpoint_missing_field():
    response = client.post("/api/v1/auth/register", json={"email": "ana@example.com"})

    assert response.status_code == 422
