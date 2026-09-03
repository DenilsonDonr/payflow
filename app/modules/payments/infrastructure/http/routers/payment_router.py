import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.composition_root import get_event_bus
from app.modules.payments.application.use_cases.create_payment_use_case import CreatePaymentUseCase
from app.modules.payments.application.use_cases.get_payment_use_case import GetPaymentUseCase
from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.infrastructure.http.schemas.payment_schemas import (
    PaymentCreateRequest,
    PaymentResponse,
)
from app.modules.payments.infrastructure.messaging.payment_created_publisher import (
    PaymentCreatedPublisher,
)
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import (
    PostgresPaymentRepository,
)


def get_create_payment_use_case() -> CreatePaymentUseCase:
    repository = PostgresPaymentRepository(connection=ConnectionDB())
    return CreatePaymentUseCase(payment_repository_port=repository)

def get_get_payment_use_case() -> GetPaymentUseCase:
    repository = PostgresPaymentRepository(connection=ConnectionDB())
    return GetPaymentUseCase(payment_repository_port=repository)

def get_payment_created_publisher() -> PaymentCreatedPublisher:
    return PaymentCreatedPublisher(event_bus=get_event_bus())

router_payment = APIRouter()

@router_payment.post(
    "/payments",
    summary="Create a new payment",
    status_code=201,
    response_model=PaymentResponse,
)
def create_payment(
    request: PaymentCreateRequest,
    use_case: CreatePaymentUseCase = Depends(get_create_payment_use_case),
    publisher: PaymentCreatedPublisher = Depends(get_payment_created_publisher),
):
    try:
        created_payment = use_case.execute(amount=request.amount, currency=request.currency)
        # The bus is synchronous: fraud evaluates and the verdict is stored before this returns.
        publisher.publish(created_payment)
        return PaymentResponse(
            id=created_payment.id,
            amount=created_payment.amount.amount,
            currency=created_payment.amount.currency,
            state=created_payment.state.value,
        )
    except PaymentAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

@router_payment.get(
    "/payments/{payment_id}",
    summary="Get a payment by ID",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: uuid.UUID,
    use_case: GetPaymentUseCase = Depends(get_get_payment_use_case),
):
    payment = use_case.execute(payment_id=payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse(
        id=payment.id,
        amount=payment.amount.amount,
        currency=payment.amount.currency,
        state=payment.state.value,
    )
