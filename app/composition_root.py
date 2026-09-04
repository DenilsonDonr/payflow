"""Wires the modules together.

This is the only module that sees `payments` and `fraud` at the same time. They never import
each other; they meet here, through the event bus.
"""

from app.modules.fraud.application.use_cases.evaluate_fraud_use_case import EvaluateFraudUseCase
from app.modules.fraud.domain.policies.amount_threshold_fraud_policy import (
    AmountThresholdFraudPolicy,
)
from app.modules.fraud.infrastructure.messaging.payment_created_subscriber import (
    PaymentCreatedSubscriber,
)
from app.modules.fraud.infrastructure.messaging.payment_verdict_publisher import (
    PaymentVerdictPublisher,
)
from app.modules.payments.application.use_cases.evaluate_payment_use_case import (
    EvaluatePaymentUseCase,
)
from app.modules.payments.infrastructure.messaging.evaluate_payment_subscriber import (
    EvaluatePaymentSubscriber,
)
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import (
    PostgresPaymentRepository,
)
from app.shared.messaging.contracts.payment_created_message import PaymentCreatedMessage
from app.shared.messaging.contracts.payment_verdict_message import PaymentVerdictMessage
from app.shared.messaging.event_bus import EventBus
from app.shared.messaging.in_process_event_bus import InProcessEventBus

_event_bus: EventBus = InProcessEventBus()


def get_event_bus() -> EventBus:
    return _event_bus


def _handle_payment_created(message: PaymentCreatedMessage) -> None:
    subscriber = PaymentCreatedSubscriber(
        evaluate_fraud_use_case=EvaluateFraudUseCase(
            fraud_policy_port=AmountThresholdFraudPolicy(),
        ),
        payment_verdict_publisher=PaymentVerdictPublisher(event_bus=_event_bus),
    )
    subscriber.handle(message)


def _handle_payment_verdict(message: PaymentVerdictMessage) -> None:
    # Built per message so the database connection is never shared: handlers run on the
    # publisher's thread, and psycopg cursors on one connection share one transaction.
    subscriber = EvaluatePaymentSubscriber(
        evaluate_payment_use_case=EvaluatePaymentUseCase(
            payment_repository_port=PostgresPaymentRepository(connection=ConnectionDB()),
        ),
    )
    subscriber.handle(message)


def register_subscriptions() -> None:
    _event_bus.subscribe(PaymentCreatedMessage, _handle_payment_created)
    _event_bus.subscribe(PaymentVerdictMessage, _handle_payment_verdict)
