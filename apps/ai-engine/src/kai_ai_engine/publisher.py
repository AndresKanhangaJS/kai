"""Publicação de eventos no `kai.events` com publisher confirms (SPEC-004 §3.1, ADR-0018).

Cada mensagem leva a propriedade AMQP `user_id=kai-ai-engine` (o broker recusa outro valor e o
Laravel exige-o), a routing key igual ao tipo e o `traceparent` também nos headers.
"""

import json
from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractExchange
from aiormq import spec

from kai_ai_engine.events import Event

EXCHANGE = "kai.events"
AMQP_USER = "kai-ai-engine"
PUBLISH_TIMEOUT_SECONDS = 10


class PublishError(RuntimeError):
    """O broker não confirmou (nack, mensagem devolvida, canal fechado ou timeout)."""


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None:
        """Só volta depois do confirm do broker; senão, `PublishError`."""
        ...


class AmqpPublisher:
    def __init__(self) -> None:
        self._exchange: AbstractExchange | None = None

    def attach(self, exchange: AbstractExchange) -> None:
        """Exchange de um canal com `publisher_confirms=True` e `on_return_raises=True`."""
        self._exchange = exchange

    async def publish(self, event: Event) -> None:
        if self._exchange is None:
            raise PublishError("sem canal de publicação")
        message = aio_pika.Message(
            body=json.dumps(event.body, ensure_ascii=False, separators=(",", ":")).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=event.id,
            type=event.type,
            user_id=AMQP_USER,
            headers={"traceparent": event.traceparent},
        )
        try:
            # mandatory: sem fila para a routing key, o broker devolve-a (on_return_raises).
            confirmation = await self._exchange.publish(
                message, routing_key=event.type, mandatory=True, timeout=PUBLISH_TIMEOUT_SECONDS
            )
        except Exception as exc:
            raise PublishError(type(exc).__name__) from None
        # Um nack ou uma devolução já levantaram; sem confirms o canal devolveria None.
        if not isinstance(confirmation, spec.Basic.Ack):
            raise PublishError("o broker não confirmou")
