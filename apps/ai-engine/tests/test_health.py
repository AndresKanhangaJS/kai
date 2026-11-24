"""AC-004-01: /health/live e /health/ready conforme o contrato health.v1."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from kai_ai_engine.inbox import ClaimState
from kai_ai_engine.llm.fake import FakeGateway
from kai_ai_engine.main import create_app

# Na CI, os contratos são montados só para leitura (scripts/ci/ai-engine.sh);
# fora do contentor, lê-os do monorepo.
_env_contracts = os.environ.get("KAI_CONTRACTS_DIR")
CONTRACTS = (
    Path(_env_contracts) if _env_contracts else Path(__file__).resolve().parents[3] / "packages" / "contracts"
)


class FakeBroker:
    def __init__(self, *, connects: bool) -> None:
        self._connects = connects
        self.is_connected = False
        self.is_consuming = False
        self.closed = False

    async def start(self) -> None:
        self.is_connected = self._connects
        self.is_consuming = self._connects

    async def close(self) -> None:
        self.is_connected = False
        self.is_consuming = False
        self.closed = True


class FakeInbox:
    def __init__(self, *, up: bool = True) -> None:
        self.up = up
        self.closed = False

    async def claim(self, message_id: str, ttl_seconds: int) -> ClaimState:
        return "new"

    async def mark_done(self, message_id: str) -> None:
        return None

    async def ping(self) -> bool:
        return self.up

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(scope="module")
def health_schema() -> Draft202012Validator:
    schema: dict[str, Any] = json.loads((CONTRACTS / "schemas" / "health.v1.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def client_for(broker: FakeBroker, inbox: FakeInbox | None = None) -> TestClient:
    return TestClient(create_app(lambda: broker, FakeGateway(), inbox or FakeInbox()))


def test_ac_004_01_live_responde_ok_conforme_o_contrato(health_schema: Draft202012Validator) -> None:
    with client_for(FakeBroker(connects=False)) as client:
        res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    health_schema.validate(res.json())


def test_ac_004_01_ready_ok_com_rabbitmq_ligado(health_schema: Draft202012Validator) -> None:
    with client_for(FakeBroker(connects=True)) as client:
        res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "checks": {"rabbitmq": "ok", "consumer": "ok", "redis": "ok"}}
    health_schema.validate(res.json())


def test_ac_004_01_negativo_ready_503_sem_rabbitmq(health_schema: Draft202012Validator) -> None:
    with client_for(FakeBroker(connects=False)) as client:
        res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "down", "checks": {"rabbitmq": "down", "consumer": "down", "redis": "ok"}}
    health_schema.validate(res.json())


def test_ac_004_01_ready_passa_a_503_quando_a_ligacao_cai() -> None:
    broker = FakeBroker(connects=True)
    with client_for(broker) as client:
        assert client.get("/health/ready").status_code == 200
        broker.is_connected = False
        assert client.get("/health/ready").status_code == 503


def test_a_ligacao_e_a_inbox_fecham_no_shutdown() -> None:
    broker, inbox = FakeBroker(connects=True), FakeInbox()
    with client_for(broker, inbox):
        pass
    assert broker.closed and inbox.closed


def test_ac_004_01_negativo_ready_503_sem_redis_ou_sem_consumidor(
    health_schema: Draft202012Validator,
) -> None:
    inbox = FakeInbox(up=False)
    with client_for(FakeBroker(connects=True), inbox) as client:
        res = client.get("/health/ready")
        assert res.status_code == 503
        assert res.json()["checks"] == {"rabbitmq": "ok", "consumer": "ok", "redis": "down"}
        health_schema.validate(res.json())
    broker = FakeBroker(connects=True)
    with client_for(broker) as client:
        broker.is_consuming = False
        res = client.get("/health/ready")
        assert res.status_code == 503 and res.json()["checks"]["consumer"] == "down"


def test_sem_documentacao_nem_openapi_expostos() -> None:
    with client_for(FakeBroker(connects=True)) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
