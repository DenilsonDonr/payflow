from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.payments.infrastructure.http.routers.payment_router import router_payment
from app.modules.payments.infrastructure.persistence.postgres_connection import (
    close_pool,
    open_pool,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Opening here keeps the first requests from paying for the handshakes the pool can do
    # up front. It does not block: an unreachable database still lets the app start.
    await open_pool()
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(router_payment, prefix="/api/v1")
