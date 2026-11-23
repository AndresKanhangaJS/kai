"""A ligação inicial ao RabbitMQ repete em background até conseguir (AC-004-01, NFR-027)."""

import asyncio
from typing import cast

from aio_pika.abc import AbstractRobustConnection

from kai_ai_engine.amqp import RabbitMqConnection
from kai_ai_engine.settings import RabbitMqSettings

SETTINGS = RabbitMqSettings(host="rabbitmq", port=5672, vhost="/kai", user="kai-ai-engine", password="x" * 24)


class FakeRobustConnection:
    def __init__(self) -> None:
        self.is_closed = False
        self.connected = asyncio.Event()
        self.connected.set()

    async def close(self) -> None:
        self.is_closed = True


def test_a_primeira_ligacao_repete_ate_conseguir_e_fica_pronta() -> None:
    calls = 0
    conn = FakeRobustConnection()

    async def flaky(_: RabbitMqSettings) -> AbstractRobustConnection:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("broker em baixo")
        return cast(AbstractRobustConnection, conn)

    async def scenario() -> None:
        broker = RabbitMqConnection(SETTINGS, connector=flaky, base_delay=0.001, max_delay=0.01)
        await broker.start()
        assert not broker.is_connected
        for _ in range(200):
            if broker.is_connected:
                break
            await asyncio.sleep(0.005)
        assert broker.is_connected
        conn.connected.clear()  # o broker cai e a ligação robusta reconecta
        assert not broker.is_connected
        conn.connected.set()
        assert broker.is_connected
        await broker.close()

    asyncio.run(scenario())
    assert calls == 3


def test_close_cancela_as_tentativas_pendentes() -> None:
    async def never(_: RabbitMqSettings) -> AbstractRobustConnection:
        raise ConnectionError("broker em baixo")

    async def scenario() -> None:
        broker = RabbitMqConnection(SETTINGS, connector=never, base_delay=0.001, max_delay=0.01)
        await broker.start()
        await asyncio.sleep(0.02)
        await broker.close()
        assert not broker.is_connected

    asyncio.run(scenario())
