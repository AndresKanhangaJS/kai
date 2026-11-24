"""Fluxo do turno contra o RabbitMQ e o AI Engine reais (stack `kai-it`, scripts/ci/integration.sh).

Fica de fora da CI unitária (sem `KAI_IT_RABBITMQ_HOST`). Cada cenário corre com o ai-engine
configurado pelo script (`KAI_IT_SCENARIO`): base, budget, retry, slow.
"""

import asyncio
import copy
import json
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import aio_pika
import pytest

from kai_ai_engine.contracts import ContractRegistry, contracts_dir

HOST = os.environ.get("KAI_IT_RABBITMQ_HOST", "")
SCENARIO = os.environ.get("KAI_IT_SCENARIO", "base")
SCENARIOS = frozenset({"base", "budget", "retry", "slow"})
TURN = "ai.conversation.turn.requested.v1"
EXAMPLES = contracts_dir() / "examples"
CONTRACTS = ContractRegistry()

pytestmark = pytest.mark.skipif(not HOST, reason="só no scripts/ci/integration.sh (stack kai-it)")


def test_scenario_is_known() -> None:
    # Um nome errado no script faria skip de tudo com exit 0 (revisão da E3.4a).
    assert SCENARIO in SCENARIOS, SCENARIO


def scenario(name: str) -> pytest.MarkDecorator:
    assert name in SCENARIOS, name
    return pytest.mark.skipif(name != SCENARIO, reason=f"cenário {name}")


@dataclass(frozen=True)
class Received:
    body: dict[str, Any]
    user_id: str | None
    headers: dict[str, Any]


def password(user: str) -> str:
    return os.environ[
        {"kai-api": "KAI_RABBITMQ_API_PASSWORD", "kai-admin": "KAI_RABBITMQ_ADMIN_PASSWORD"}[user]
    ]


async def connect(user: str) -> aio_pika.abc.AbstractConnection:
    return await aio_pika.connect(
        host=HOST, login=user, password=password(user), virtualhost="/kai", timeout=10
    )


def command(**limits: Any) -> dict[str, Any]:
    body: dict[str, Any] = copy.deepcopy(
        json.loads((EXAMPLES / TURN / "valid" / "minimo.json").read_text(encoding="utf-8"))
    )
    user_message_id = str(uuid.uuid4())
    body["id"] = str(uuid.uuid7())
    body["correlation_id"] = str(uuid.uuid4())
    body["idempotency_key"] = f"turn:{user_message_id}"
    body["payload"]["user_message_id"] = user_message_id
    body["payload"]["run_id"] = str(uuid.uuid4())
    body["payload"]["messages"][-1]["message_id"] = user_message_id
    body["payload"]["limits"].update(limits)
    return body


def publish(body: dict[str, Any] | bytes, *, user: str = "kai-api", user_id: str | None = "kai-api") -> None:
    async def go() -> None:
        connection = await connect(user)
        async with connection:
            channel = await connection.channel(publisher_confirms=True)
            exchange = await channel.get_exchange("kai.commands", ensure=False)
            raw = body if isinstance(body, bytes) else json.dumps(body).encode()
            await exchange.publish(
                aio_pika.Message(
                    raw,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    user_id=user_id,
                ),
                routing_key=TURN,
                mandatory=True,
            )

    asyncio.run(go())


def drain(
    queue: str, *, seconds: float, until: Callable[[list[Received]], bool] | None = None
) -> list[Received]:
    """Lê (como kai-admin) até `until` ser verdade ou o tempo acabar."""

    async def go() -> list[Received]:
        out: list[Received] = []
        connection = await connect("kai-admin")
        async with connection:
            channel = await connection.channel()
            q = await channel.get_queue(queue, ensure=False)
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                message = await q.get(no_ack=True, fail=False)
                if message is None:
                    if until is not None and until(out):
                        break
                    await asyncio.sleep(0.2)
                    continue
                out.append(Received(json.loads(message.body), message.user_id, dict(message.headers)))
        return out

    return asyncio.run(go())


@pytest.fixture(autouse=True)
def clean_queues() -> None:
    async def go() -> None:
        connection = await connect("kai-admin")
        async with connection:
            channel = await connection.channel()
            for name in ("kai-api.events", "ai-engine.commands.dlq"):
                await (await channel.get_queue(name, ensure=False)).purge()

    asyncio.run(go())


def terminal_for(cmd: dict[str, Any]) -> Callable[[list[Received]], bool]:
    def done(events: list[Received]) -> bool:
        return any(
            e.body["causation_id"] == cmd["id"] and e.body["type"].startswith("ai.conversation.turn.")
            for e in events
        )

    return done


def events_for(cmd: dict[str, Any], *, seconds: float = 30) -> list[Received]:
    events = drain("kai-api.events", seconds=seconds, until=terminal_for(cmd))
    for event in events:
        assert CONTRACTS.violations(event.body["type"], event.body) == [], event.body["type"]
        assert event.user_id == "kai-ai-engine"
        assert event.headers.get("traceparent") == event.body["traceparent"]
    return [e for e in events if e.body["causation_id"] == cmd["id"]]


def of(events: list[Received], suffix: str) -> list[dict[str, Any]]:
    return [e.body for e in events if e.body["type"].endswith(suffix)]


@scenario("base")
def test_ac_004_02_turno_real_da_completed_e_usage_validos() -> None:
    cmd = command()
    publish(cmd)
    events = events_for(cmd)
    (completed,) = of(events, "turn.completed.v1")
    (usage,) = of(events, "usage.recorded.v1")
    assert completed["payload"]["content"].startswith("Resposta fake: ")
    assert completed["payload"]["user_message_id"] == cmd["payload"]["user_message_id"]
    assert completed["correlation_id"] == cmd["correlation_id"]
    assert usage["payload"]["provider"] == "fake"


@scenario("base")
def test_ac_004_04_invalidos_e_sem_user_id_vao_para_a_dlq_sem_eventos() -> None:
    directory = EXAMPLES / TURN / "invalid"
    invalid = [p for p in sorted(directory.iterdir()) if p.stem != "expected-errors"]
    for path in invalid:
        publish(path.read_bytes())
    # Válida, mas publicada pelo admin sem o user_id do produtor.
    publish(command(), user="kai-admin", user_id=None)
    expected = len(invalid) + 1
    dead = drain("ai-engine.commands.dlq", seconds=30, until=lambda got: len(got) >= expected)
    assert len(dead) == expected
    for message in dead:
        (death,) = [d for d in message.headers["x-death"] if d["queue"] == "ai-engine.commands"]
        assert death["reason"] == "rejected"
    assert drain("kai-api.events", seconds=2) == []


@scenario("base")
def test_ac_004_05_reentrega_do_mesmo_id_nao_gera_de_novo() -> None:
    cmd = command()
    publish(cmd)
    first = events_for(cmd)
    assert len(of(first, "turn.completed.v1")) == 1
    publish(cmd)
    time.sleep(3)
    assert drain("kai-api.events", seconds=2) == []
    assert drain("ai-engine.commands.dlq", seconds=1) == []


@scenario("budget")
def test_ac_004_07_orcamento_excedido_sem_chamada_nem_usage() -> None:
    cmd = command(max_cost_usd="0.01")
    publish(cmd)
    events = events_for(cmd)
    (failed,) = of(events, "turn.failed.v1")
    assert failed["payload"]["reason"] == "budget_exceeded"
    assert of(events, "usage.recorded.v1") == []


@scenario("retry")
def test_ac_004_09_falhas_transitorias_antes_do_delta_repetem_e_concluem() -> None:
    cmd = command()
    publish(cmd)
    events = events_for(cmd)
    assert len(of(events, "turn.completed.v1")) == 1
    assert len(of(events, "usage.recorded.v1")) == 1


@scenario("slow")
def test_ac_004_06_timeout_com_usage_parcial() -> None:
    cmd = command(timeout_seconds=2)
    publish(cmd)
    events = events_for(cmd)
    (failed,) = of(events, "turn.failed.v1")
    assert failed["payload"]["reason"] == "timeout"
    (usage,) = of(events, "usage.recorded.v1")
    assert usage["payload"]["output_tokens"] > 0
