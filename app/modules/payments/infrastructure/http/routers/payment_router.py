from fastapi import APIRouter, Depends, HTTPException

from app.modules.payments.domain.exceptions.payment_already_exists import PaymentAlreadyExistsError
from app.modules.payments.application.use_cases.create_payment_use_case import CreatePaymentUseCase
from app.modules.payments.infrastructure.http.schemas.payment_schemas import PaymentCreateRequest, PaymentResponse
from app.modules.payments.infrastructure.persistence.postgres_connection import ConnectionDB
from app.modules.payments.infrastructure.persistence.repository.postgres_payment_repository import PostgresPaymentRepository


def get_create_payment_use_case() -> CreatePaymentUseCase:
    repository = PostgresPaymentRepository(connection=ConnectionDB())
    return CreatePaymentUseCase(payment_repository_port=repository)


router_payment = APIRouter()

@router_payment.post("/payments", summary="Create a new payment", status_code=201, response_model=PaymentResponse)
def create_payment(request: PaymentCreateRequest, use_case: CreatePaymentUseCase = Depends(get_create_payment_use_case)):
    try:
        created_payment = use_case.execute(amount=request.amount, currency=request.currency)
        return PaymentResponse(
            id=created_payment.id,
            amount=created_payment.amount.amount,
            currency=created_payment.amount.currency,
            state=created_payment.state.value,
        )
    except PaymentAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
