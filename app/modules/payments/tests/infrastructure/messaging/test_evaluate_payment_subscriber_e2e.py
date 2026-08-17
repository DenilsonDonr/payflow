import uuid

import pytest
from fastapi.testclient import TestClient

from app.modules.payments.application.use_cases.evaluate_payment_use_case import (
    EvaluatePaymentUseCase,
)
from app.modules.payments.domain.entities.payment import PaymentState
from app.modules.payments.infrastructure.messaging.evaluate_payment_subscriber import (
    EvaluatePaymentSubscriber,
)
from app.modules.payments.infrastructure.messaging.payment_verdict_message import (
    PaymentVerdictMessage,
)
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import (
    PostgresPaymentRepository,
)
from app.shared.messaging.in_process_event_bus import InProcessEventBus
from main import app

client = TestClient(app)

pytestmark = pytest.mark.integration


class TestEvaluatePaymentE2E:
    def test_approved_verdict_message_transitions_payment_to_approved(
        self, payment_cleanup: dict[str, str | None]
    ) -> None:
        created_payment = payment_cleanup

        data_request = {
            "amount": "100.00",
            "currency": "USD",
        }

        response = client.post("/api/v1/payments", json=data_request)

        assert response.status_code == 201

        id = response.json().get("id")
        created_payment["payment_id"] = id  # Store the id so the fixture cleans it up

        payment_id = uuid.UUID(id)

        payment_repository = PostgresPaymentRepository(connection=ConnectionDB())
        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        subscriber = EvaluatePaymentSubscriber(evaluate_payment_use_case=evaluate_payment_use_case)

        bus = InProcessEventBus()
        bus.subscribe(PaymentVerdictMessage, subscriber.handle)

        message = PaymentVerdictMessage(payment_id=payment_id, verdict="approved")
        bus.publish(message)

        updated_payment = payment_repository.get_payment_by_id(payment_id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.APPROVED

    def test_rejected_verdict_message_transitions_payment_to_rejected(
        self, payment_cleanup: dict[str, str | None]
    ) -> None:
        created_payment = payment_cleanup

        data_request = {
            "amount": "100.00",
            "currency": "USD",
        }

        response = client.post("/api/v1/payments", json=data_request)

        assert response.status_code == 201

        id = response.json().get("id")
        created_payment["payment_id"] = id  # Store the id so the fixture cleans it up

        payment_id = uuid.UUID(id)

        payment_repository = PostgresPaymentRepository(connection=ConnectionDB())
        evaluate_payment_use_case = EvaluatePaymentUseCase(payment_repository_port=payment_repository)
        subscriber = EvaluatePaymentSubscriber(evaluate_payment_use_case=evaluate_payment_use_case)

        bus = InProcessEventBus()
        bus.subscribe(PaymentVerdictMessage, subscriber.handle)

        message = PaymentVerdictMessage(payment_id=payment_id, verdict="rejected")
        bus.publish(message)

        updated_payment = payment_repository.get_payment_by_id(payment_id)

        assert updated_payment is not None
        assert updated_payment.state == PaymentState.REJECTED
