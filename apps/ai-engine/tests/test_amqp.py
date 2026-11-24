"""Ligação ao RabbitMQ: a primeira ligação e as reconexões repetem em background, e o consumidor
é recriado em cada ligação (AC-004-01, NFR-027; reconexão própria, E3.4a)."""

import asyncio
from collections.abc import Callable
from typing import Any, cast

from aio_pika.abc import AbstractConnection

from kai_ai_engine.amqp import RabbitMqConnection
from kai_ai_engine.settings import RabbitMqSettings

SETTINGS = RabbitMqSettings(host="rabbitmq", port=5672, vhost="/kai", user="kai-ai-engine", password="x" * 24)


class Callbacks:
    def __init__(self) -> None:
        self.items: list[Callable[..., Any]] = []

    def add(self, callback: Callable[..., Any]) -> None:
        self.items.append(callback)


class FakeConnection:
    def __init__(self) -> None:
        self.is_closed = False
        self.close_callbacks = Callbacks()

    def drop(self) -> None:
        """O broker cai: a ligação fecha e avisa os callbacks."""
        self.is_closed = True
        for callback in self.close_callbacks.items:
            callback(self, ConnectionError("broker reiniciado"))

    async def close(self) -> None:
        self.is_closed = True


class FakeConsumer:
    def __init__(self, *, fail_first: int = 0) -> None:
        self.attached: list[FakeConnection] = []
        self.fail_first = fail_first
        self.closed = False

    @property
    def is_consuming(self) -> bool:
        return bool(self.attached) and not self.attached[-1].is_closed

    async def attach(self, connection: AbstractConnection) -> None:
        if self.fail_first:
            self.fail_first -= 1
            raise RuntimeError("fila inexistente")
        self.attached.append(cast(FakeConnection, connection))

    async def close(self) -> None:
        self.closed = True


async def until(condition: Callable[[], bool]) -> None:
    for _ in range(400):
        if condition():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("condição não chegou a ser verdade")


def make(connector: Any, consumer: FakeConsumer | None = None) -> RabbitMqConnection:
    return RabbitMqConnection(
        SETTINGS, connector=connector, base_delay=0.001, max_delay=0.01, consumer=consumer
    )


def test_a_primeira_ligacao_repete_ate_conseguir_e_fica_pronta() -> None:
    calls = 0

    async def flaky(_: RabbitMqSettings) -> AbstractConnection:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("broker em baixo")
        return cast(AbstractConnection, FakeConnection())

    async def scenario() -> None:
        consumer = FakeConsumer()
        broker = make(flaky, consumer)
        await broker.start()
        assert not broker.is_connected and not broker.is_consuming
        await until(lambda: broker.is_consuming)
        await broker.close()
        assert consumer.closed and not broker.is_connected

    asyncio.run(scenario())
    assert calls == 3


def test_quando_a_ligacao_cai_liga_outra_vez_e_recria_o_consumidor() -> None:
    connections: list[FakeConnection] = []

    async def connector(_: RabbitMqSettings) -> AbstractConnection:
        connections.append(FakeConnection())
        return cast(AbstractConnection, connections[-1])

    async def scenario() -> None:
        consumer = FakeConsumer()
        broker = make(connector, consumer)
        await broker.start()
        await until(lambda: broker.is_consuming)
        connections[0].drop()
        # Logo a seguir à queda, a readiness reflecte-a (não fica "ok" sem consumidor).
        assert not broker.is_connected and not broker.is_consuming
        await until(lambda: len(consumer.attached) == 2 and broker.is_consuming)
        assert consumer.attached[1] is connections[1]
        await broker.close()

    asyncio.run(scenario())


def test_uma_falha_ao_criar_o_consumidor_fecha_a_ligacao_e_repete() -> None:
    connections: list[FakeConnection] = []

    async def connector(_: RabbitMqSettings) -> AbstractConnection:
        connections.append(FakeConnection())
        return cast(AbstractConnection, connections[-1])

    async def scenario() -> None:
        consumer = FakeConsumer(fail_first=2)
        broker = make(connector, consumer)
        await broker.start()
        await until(lambda: broker.is_consuming)
        assert len(connections) == 3
        assert connections[0].is_closed and connections[1].is_closed
        await broker.close()

    asyncio.run(scenario())


def test_close_cancela_as_tentativas_pendentes() -> None:
    async def never(_: RabbitMqSettings) -> AbstractConnection:
        raise ConnectionError("broker em baixo")

    async def scenario() -> None:
        broker = make(never)
        await broker.start()
        await asyncio.sleep(0.02)
        await broker.close()
        assert not broker.is_connected

    asyncio.run(scenario())
