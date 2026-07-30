from fastapi import FastAPI
from app.modules.payments.infrastructure.http.routers.payment_router import router_payment

app = FastAPI()

app.include_router(router_payment, prefix="/api/v1")
