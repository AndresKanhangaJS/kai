"""Aplicação FastAPI do AI Engine (SPEC-004). Sem porta publicada no host (ADR-0010)."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from kai_ai_engine.amqp import BrokerConnection, RabbitMqConnection
from kai_ai_engine.consumer import CommandConsumer
from kai_ai_engine.contracts import ContractRegistry
from kai_ai_engine.health import router as health_router
from kai_ai_engine.inbox import Inbox, RedisInbox
from kai_ai_engine.llm.factory import build_gateway
from kai_ai_engine.llm.gateway import LLMGateway
from kai_ai_engine.logging import configure_logging
from kai_ai_engine.publisher import AmqpPublisher
from kai_ai_engine.settings import load_settings
from kai_ai_engine.turns import TurnHandler


def create_app(broker_factory: Callable[[], BrokerConnection], gateway: LLMGateway, inbox: Inbox) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        broker = broker_factory()
        app.state.broker = broker
        app.state.llm = gateway
        app.state.inbox = inbox
        await broker.start()
        try:
            yield
        finally:
            # O broker fecha primeiro: o consumidor termina os turnos a meio antes do resto.
            await broker.close()
            await gateway.aclose()
            await inbox.aclose()

    # Sem /docs nem /openapi.json: o contrato vive em packages/contracts.
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(health_router)
    return app


def build() -> FastAPI:
    """Ponto de entrada do uvicorn (`--factory`): lê o ambiente e falha cedo."""
    configure_logging()
    settings = load_settings()
    gateway = build_gateway(settings.llm)
    inbox = RedisInbox(settings.redis)
    publisher = AmqpPublisher()
    handler = TurnHandler(gateway=gateway, inbox=inbox, publisher=publisher, contracts=ContractRegistry())
    consumer = CommandConsumer(handler.handle, publisher)
    return create_app(lambda: RabbitMqConnection(settings.rabbitmq, consumer=consumer), gateway, inbox)
