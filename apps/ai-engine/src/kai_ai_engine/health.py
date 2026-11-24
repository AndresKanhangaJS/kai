"""`/health/live` e `/health/ready` (contrato `health.v1`, NFR-027, AC-004-01).

As respostas não levam versões, hosts nem mensagens de erro.
"""

import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from kai_ai_engine.amqp import BrokerConnection
from kai_ai_engine.inbox import Inbox

router = APIRouter()

CheckState = Literal["ok", "down"]
REDIS_PING_SECONDS = 2.0


@router.get("/health/live")
async def live() -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def _redis_ok(inbox: Inbox) -> bool:
    try:
        async with asyncio.timeout(REDIS_PING_SECONDS):
            return await inbox.ping()
    except TimeoutError:
        return False


@router.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    broker: BrokerConnection = request.app.state.broker
    inbox: Inbox = request.app.state.inbox
    checks: dict[str, CheckState] = {
        "rabbitmq": "ok" if broker.is_connected else "down",
        "consumer": "ok" if broker.is_consuming else "down",
        "redis": "ok" if await _redis_ok(inbox) else "down",
    }
    healthy = all(state == "ok" for state in checks.values())
    return JSONResponse(
        {"status": "ok" if healthy else "down", "checks": checks},
        status_code=200 if healthy else 503,
    )
