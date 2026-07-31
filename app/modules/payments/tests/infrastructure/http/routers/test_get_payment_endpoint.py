import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.modules.payments.domain.entities.payment import Payment
from app.modules.payments.domain.value_objects.money import Money
from app.modules.payments.application.use_cases.get_payment_use_case import GetPaymentUseCase
from app.modules.payments.infrastructure.http.routers.payment_router import get_get_payment_use_case
from app.modules.payments.tests.fakes.in_memory_payment_repository import InMemoryPaymentRepository
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()

def test_get_payment_endpoint():
    object_in_memory_repository = InMemoryPaymentRepository()

    payment = Payment(id=uuid.uuid4(), amount=Money(amount=Decimal("100.00"), currency="USD"))

    object_in_memory_repository.add(payment)

    app.dependency_overrides[get_get_payment_use_case] = lambda: GetPaymentUseCase(payment_repository_port=object_in_memory_repository)

    response = client.get(f"/api/v1/payments/{payment.id}")

    assert response.status_code == 200
    assert response.json().get("id") == str(payment.id)
    assert response.json().get("amount") == str(payment.amount.amount)
    assert response.json().get("currency") == payment.amount.currency

def test_get_payment_endpoint_not_found():
    app.dependency_overrides[get_get_payment_use_case] = lambda: GetPaymentUseCase(payment_repository_port=InMemoryPaymentRepository())

    non_existent_payment_id = uuid.uuid4()

    response = client.get(f"/api/v1/payments/{non_existent_payment_id}")

    assert response.status_code == 404

def test_get_payment_endpoint_invalid_uuid():
    invalid_uuid = "invalid-uuid"
    response = client.get(f"/api/v1/payments/{invalid_uuid}")
    assert response.status_code == 422
