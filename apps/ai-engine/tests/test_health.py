"""AC-004-01: /health/live e /health/ready conforme o contrato health.v1."""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

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
        self.closed = False

    async def start(self) -> None:
        self.is_connected = self._connects

    async def close(self) -> None:
        self.is_connected = False
        self.closed = True


@pytest.fixture(scope="module")
def health_schema() -> Draft202012Validator:
    schema: dict[str, Any] = json.loads((CONTRACTS / "schemas" / "health.v1.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def client_for(broker: FakeBroker) -> TestClient:
    return TestClient(create_app(lambda: broker, FakeGateway()))


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
    assert res.json() == {"status": "ok", "checks": {"rabbitmq": "ok"}}
    health_schema.validate(res.json())


def test_ac_004_01_negativo_ready_503_sem_rabbitmq(health_schema: Draft202012Validator) -> None:
    with client_for(FakeBroker(connects=False)) as client:
        res = client.get("/health/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "down", "checks": {"rabbitmq": "down"}}
    health_schema.validate(res.json())


def test_ac_004_01_ready_passa_a_503_quando_a_ligacao_cai() -> None:
    broker = FakeBroker(connects=True)
    with client_for(broker) as client:
        assert client.get("/health/ready").status_code == 200
        broker.is_connected = False
        assert client.get("/health/ready").status_code == 503


def test_a_ligacao_fecha_no_shutdown() -> None:
    broker = FakeBroker(connects=True)
    with client_for(broker):
        pass
    assert broker.closed


def test_sem_documentacao_nem_openapi_expostos() -> None:
    with client_for(FakeBroker(connects=True)) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
