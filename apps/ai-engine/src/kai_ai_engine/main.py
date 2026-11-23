"""Aplicação FastAPI do AI Engine (SPEC-004). Sem porta publicada no host (ADR-0010)."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from kai_ai_engine.amqp import BrokerConnection, RabbitMqConnection
from kai_ai_engine.health import router as health_router
from kai_ai_engine.logging import configure_logging
from kai_ai_engine.settings import load_settings


def create_app(broker_factory: Callable[[], BrokerConnection]) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        broker = broker_factory()
        app.state.broker = broker
        await broker.start()
        try:
            yield
        finally:
            await broker.close()

    # Sem /docs nem /openapi.json: o contrato vive em packages/contracts.
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(health_router)
    return app


def build() -> FastAPI:
    """Ponto de entrada do uvicorn (`--factory`): lê o ambiente e falha cedo."""
    configure_logging()
    settings = load_settings()
    return create_app(lambda: RabbitMqConnection(settings.rabbitmq))
