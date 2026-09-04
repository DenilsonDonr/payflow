import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.modules.payments.application.use_cases.create_payment_use_case import CreatePaymentUseCase
from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.domain.ports.payment_repository_port import PaymentRepositoryPort
from app.modules.payments.infrastructure.http.routers.payment_router import (
    get_create_payment_use_case,
    get_payment_created_publisher,
)
from app.modules.payments.infrastructure.http.schemas.payment_schemas import PaymentCreateRequest
from app.modules.payments.infrastructure.messaging.payment_created_publisher import (
    PaymentCreatedPublisher,
)
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository
from app.shared.messaging.in_process_event_bus import InProcessEventBus
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_event_bus():
    # A bus of its own, with nobody subscribed: these tests exercise the endpoint, not the
    # wiring. On the application bus the POST would run fraud and reach the real database.
    app.dependency_overrides[get_payment_created_publisher] = lambda: PaymentCreatedPublisher(
        event_bus=InProcessEventBus()
    )


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


class DuplicatePaymentRepository(PaymentRepositoryPort):
    def get_payment_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        raise NotImplementedError

    def create_payment(self, payment: Payment) -> Payment:
        raise PaymentAlreadyExistsError(f"Payment with ID {payment.id} already exists.")

    def update_payment(self, payment: Payment) -> None:
        raise NotImplementedError("This test double does not support update_payment.")


def test_create_payment_endpoint():
    app.dependency_overrides[get_create_payment_use_case] = lambda: CreatePaymentUseCase(payment_repository_port=InMemoryPaymentRepository())

    data_request = PaymentCreateRequest(
        amount=Decimal("100.00"),
        currency="USD",
    )

    response = client.post("/api/v1/payments", json=data_request.model_dump(mode='json'))

    assert response.status_code == 201

def test_create_payment_endpoint_invalid_currency():
    app.dependency_overrides[get_create_payment_use_case] = lambda: CreatePaymentUseCase(payment_repository_port=InMemoryPaymentRepository())

    # Send raw JSON so FastAPI parses and validates the body itself (returning 422);
    # building PaymentCreateRequest(...) here would instead fail inside the test.
    response = client.post("/api/v1/payments", json={"amount": "100.00", "currency": "US"})

    assert response.status_code == 422

def test_create_payment_endpoint_duplicate_error():
    app.dependency_overrides[get_create_payment_use_case] = lambda: CreatePaymentUseCase(payment_repository_port=DuplicatePaymentRepository())

    data_request = PaymentCreateRequest(
        amount=Decimal("100.00"),
        currency="USD",
    )

    response = client.post("/api/v1/payments", json=data_request.model_dump(mode='json'))

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
