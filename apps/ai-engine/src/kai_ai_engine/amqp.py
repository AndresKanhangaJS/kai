"""Ligação ao RabbitMQ (ADR-0016: aio-pika). Na E3.2 serve só a readiness; o
consumidor de `ai-engine.commands` entra na E3.4."""

import asyncio
import contextlib
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from kai_ai_engine.settings import RabbitMqSettings

log = logging.getLogger(__name__)

Connector = Callable[[RabbitMqSettings], Awaitable[AbstractRobustConnection]]


class BrokerConnection(Protocol):
    @property
    def is_connected(self) -> bool: ...

    async def start(self) -> None: ...

    async def close(self) -> None: ...


async def _connect(s: RabbitMqSettings) -> AbstractRobustConnection:
    return await aio_pika.connect_robust(
        host=s.host,
        port=s.port,
        login=s.user,
        password=s.password,
        virtualhost=s.vhost,
        client_properties={"connection_name": "kai-ai-engine"},
        # Sem timeout, um SYN descartado pendura a primeira tentativa para sempre.
        timeout=10,
    )


class RabbitMqConnection:
    """Ligação robusta. O `connect_robust` só reconecta depois da primeira ligação;
    a primeira é tentada em background, com backoff exponencial e jitter, para o
    serviço arrancar (live) mesmo com o broker em baixo e ficar pronto quando ele
    voltar. A readiness segue o estado real da ligação."""

    def __init__(
        self,
        settings: RabbitMqSettings,
        connector: Connector = _connect,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self._settings = settings
        self._connector = connector
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._connection: AbstractRobustConnection | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def is_connected(self) -> bool:
        # `is_closed` só muda com um close() pedido; numa queda do broker, a ligação
        # robusta limpa o evento `connected` enquanto reconecta.
        c = self._connection
        return c is not None and not c.is_closed and c.connected.is_set()

    async def start(self) -> None:
        self._task = asyncio.create_task(self._connect_until_ready(), name="rabbitmq-connect")

    async def _connect_until_ready(self) -> None:
        attempt = 0
        while True:
            try:
                self._connection = await self._connector(self._settings)
            except Exception:
                # Só a classe (JsonFormatter): a mensagem pode conter o URL de ligação.
                log.warning("rabbitmq_connect_failed", exc_info=True, extra={"fields": {"attempt": attempt}})
                delay = min(self._max_delay, self._base_delay * 2**attempt)
                attempt += 1
                await asyncio.sleep(delay * random.uniform(0.5, 1.0))  # noqa: S311 (jitter, não criptografia)
                continue
            log.info("rabbitmq_connected", extra={"fields": {"attempt": attempt}})
            return

    async def close(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
