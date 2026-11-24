"""Consumidor de `ai-engine.commands` (SPEC-004 §3, ADR-0018).

O utilizador `kai-ai-engine` não tem permissão `configure`: a fila e o exchange obtêm-se sem
os declarar. Cada mensagem corre numa task; o `prefetch` limita quantas correm ao mesmo tempo.
No shutdown deixa de consumir, espera pelas que estão a meio e devolve as restantes à fila.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractIncomingMessage,
    AbstractQueue,
)

from kai_ai_engine.publisher import EXCHANGE, AmqpPublisher

log = logging.getLogger(__name__)

QUEUE = "ai-engine.commands"
PREFETCH = 4
DRAIN_SECONDS = 10.0

Handler = Callable[[AbstractIncomingMessage], Awaitable[None]]


class CommandConsumer:
    def __init__(
        self,
        handler: Handler,
        publisher: AmqpPublisher,
        *,
        prefetch: int = PREFETCH,
        drain_seconds: float = DRAIN_SECONDS,
    ) -> None:
        self._handler = handler
        self._publisher = publisher
        self._prefetch = prefetch
        self._drain_seconds = drain_seconds
        self._channel: AbstractChannel | None = None
        self._publish_channel: AbstractChannel | None = None
        self._connection: AbstractConnection | None = None
        self._closing = False
        self._background: set[asyncio.Task[None]] = set()
        self._queue: AbstractQueue | None = None
        self._tag: str | None = None
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def is_consuming(self) -> bool:
        channels = (self._channel, self._publish_channel)
        return self._tag is not None and all(c is not None and not c.is_closed for c in channels)

    async def attach(self, connection: AbstractConnection) -> None:
        """Em cada (re)ligação: canais novos, exchange de publicação e `basic.consume`."""
        self._tag = None
        self._connection = connection
        # Canal próprio para publicar, com confirms; uma mensagem sem fila é devolvida e falha.
        publish_channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
        publish_channel.close_callbacks.add(self._on_channel_closed)
        self._publisher.attach(await publish_channel.get_exchange(EXCHANGE, ensure=False))
        self._publish_channel = publish_channel
        channel = await connection.channel()
        channel.close_callbacks.add(self._on_channel_closed)
        await channel.set_qos(prefetch_count=self._prefetch)
        queue = await channel.get_queue(QUEUE, ensure=False)
        self._tag = await queue.consume(self._on_message)
        self._channel, self._queue = channel, queue
        log.info("consumer_started", extra={"fields": {"queue": QUEUE, "prefetch": self._prefetch}})

    def _on_channel_closed(self, *_: object) -> None:
        """Um canal fechou sem a ligação cair (ex.: PRECONDITION_FAILED): fecha a ligação para
        a reconexão recriar tudo (revisão da E3.4a)."""
        connection = self._connection
        if self._closing or connection is None or connection.is_closed:
            return
        log.warning("amqp_channel_closed")
        task = asyncio.get_running_loop().create_task(connection.close())
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        task = asyncio.create_task(self._run(message))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, message: AbstractIncomingMessage) -> None:
        try:
            await self._handler(message)
        except asyncio.CancelledError:
            # Shutdown a meio: volta à fila; a inbox (`processing`) deixa outra instância retomá-lo.
            with contextlib.suppress(Exception):
                await message.nack(requeue=True)
            raise
        except Exception:
            log.exception("consumer_unhandled_error")
            with contextlib.suppress(Exception):
                await message.reject(requeue=False)

    async def close(self) -> None:
        self._closing = True
        if self._queue is not None and self._tag is not None:
            with contextlib.suppress(Exception):
                await self._queue.cancel(self._tag)
        self._tag = None
        if self._tasks:
            _, pending = await asyncio.wait(set(self._tasks), timeout=self._drain_seconds)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if pending:
                log.warning("consumer_drain_timeout", extra={"fields": {"requeued": len(pending)}})
        for channel in (self._channel, self._publish_channel):
            if channel is not None:
                with contextlib.suppress(Exception):
                    await channel.close()
        self._channel = self._publish_channel = None
