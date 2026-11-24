"""Ligação ao RabbitMQ (ADR-0016: aio-pika), com reconexão própria.

Não usa o `connect_robust`: na E3.4a, com o broker reiniciado, o aio-pika 10.2.3 reabria os
canais mas não restaurava o consumidor (`consumer_count 0` e `RuntimeError` no `_on_close` do
canal robusto), e a readiness continuava a dizer "ok". Aqui, quando a ligação cai, liga-se outra
vez, com backoff exponencial e jitter, e o consumidor volta a criar os canais e o `basic.consume`.
A primeira ligação também é feita em background: o serviço arranca (live) com o broker em baixo e
fica pronto quando ele voltar.
"""

import asyncio
import contextlib
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import aio_pika
from aio_pika.abc import AbstractConnection

from kai_ai_engine.settings import RabbitMqSettings

log = logging.getLogger(__name__)

Connector = Callable[[RabbitMqSettings], Awaitable[AbstractConnection]]


class Consumer(Protocol):
    @property
    def is_consuming(self) -> bool: ...

    async def attach(self, connection: AbstractConnection) -> None: ...

    async def close(self) -> None: ...


class BrokerConnection(Protocol):
    @property
    def is_connected(self) -> bool: ...

    @property
    def is_consuming(self) -> bool: ...

    async def start(self) -> None: ...

    async def close(self) -> None: ...


async def _connect(s: RabbitMqSettings) -> AbstractConnection:
    return await aio_pika.connect(
        host=s.host,
        port=s.port,
        login=s.user,
        password=s.password,
        virtualhost=s.vhost,
        client_properties={"connection_name": "kai-ai-engine"},
        # Sem timeout, um SYN descartado pendura a tentativa para sempre.
        timeout=10,
    )


class RabbitMqConnection:
    def __init__(
        self,
        settings: RabbitMqSettings,
        connector: Connector = _connect,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        consumer: Consumer | None = None,
    ) -> None:
        self._settings = settings
        self._connector = connector
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._consumer = consumer
        self._connection: AbstractConnection | None = None
        self._lost = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_connected(self) -> bool:
        c = self._connection
        return c is not None and not c.is_closed

    @property
    def is_consuming(self) -> bool:
        return self._consumer is not None and self.is_connected and self._consumer.is_consuming

    async def start(self) -> None:
        self._task = asyncio.create_task(self._maintain(), name="rabbitmq-connection")

    async def _maintain(self) -> None:
        while True:
            await self._connect_until_ready()
            await self._lost.wait()
            log.warning("rabbitmq_connection_lost")
            self._connection = None

    async def _connect_until_ready(self) -> None:
        attempt = 0
        while True:
            self._lost.clear()
            connection: AbstractConnection | None = None
            try:
                connection = await self._connector(self._settings)
                connection.close_callbacks.add(self._on_close)
                self._connection = connection
                if self._consumer is not None:
                    await self._consumer.attach(connection)
            except Exception:
                # Só a classe (JsonFormatter): a mensagem pode conter o URL de ligação.
                log.warning("rabbitmq_connect_failed", exc_info=True, extra={"fields": {"attempt": attempt}})
                self._connection = None
                if connection is not None:
                    with contextlib.suppress(Exception):
                        await connection.close()
                delay = min(self._max_delay, self._base_delay * 2**attempt)
                attempt += 1
                await asyncio.sleep(delay * random.uniform(0.5, 1.0))  # noqa: S311 (jitter, não criptografia)
                continue
            log.info("rabbitmq_connected", extra={"fields": {"attempt": attempt}})
            return

    def _on_close(self, *_: Any) -> None:
        self._lost.set()

    async def close(self) -> None:
        # Primeiro pára a reconexão: uma queda durante o drain não pode voltar a consumir.
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._consumer is not None:
            # Depois deixa de consumir e espera pelos turnos a meio (NFR-027).
            await self._consumer.close()
        connection, self._connection = self._connection, None
        if connection is not None:
            with contextlib.suppress(Exception):
                await connection.close()
