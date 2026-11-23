"""`/health/live` e `/health/ready` (contrato `health.v1`, NFR-027, AC-004-01).

As respostas não levam versões, hosts nem mensagens de erro.
"""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from kai_ai_engine.amqp import BrokerConnection

router = APIRouter()

CheckState = Literal["ok", "down"]


@router.get("/health/live")
async def live() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@router.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    broker: BrokerConnection = request.app.state.broker
    checks: dict[str, CheckState] = {"rabbitmq": "ok" if broker.is_connected else "down"}
    healthy = all(state == "ok" for state in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "down", "checks": checks},
        status_code=200 if healthy else 503,
    )
