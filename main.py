from fastapi import FastAPI

from app.composition_root import register_subscriptions
from app.modules.payments.infrastructure.http.routers.payment_router import router_payment

register_subscriptions()

app = FastAPI()

app.include_router(router_payment, prefix="/api/v1")
