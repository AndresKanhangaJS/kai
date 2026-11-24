"""Eventos Python → Laravel (envelope v1, SPEC-003): `turn.completed`, `turn.failed` e
`model.usage.recorded`. Cada evento é validado contra o seu schema antes de sair.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from kai_ai_engine.contracts import ContractRegistry
from kai_ai_engine.llm.gateway import Cost, Provider, Usage
from kai_ai_engine.llm.pricing import format_usd

PRODUCER = "kai-ai-engine"
TURN_COMPLETED = "ai.conversation.turn.completed.v1"
TURN_FAILED = "ai.conversation.turn.failed.v1"
USAGE_RECORDED = "ai.model.usage.recorded.v1"

FailReason = Literal[
    "provider_unavailable",
    "provider_error",
    "timeout",
    "budget_exceeded",
    "cancelled",
    "invalid_request",
    "internal_error",
]
FinishReason = Literal["end_turn", "max_output_tokens", "stop_sequence"]


class InvalidEventError(RuntimeError):
    """Um evento nosso não valida no contrato: é um bug, nunca se publica."""


@dataclass(frozen=True)
class TurnContext:
    """IDs do comando que causou os eventos (nunca o conteúdo)."""

    command_id: str
    correlation_id: str
    traceparent: str
    user_id: int
    conversation_id: str
    user_message_id: str
    run_id: str
    mission_id: str | None = None


@dataclass(frozen=True)
class Event:
    type: str
    body: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.body["id"])

    @property
    def traceparent(self) -> str:
        return str(self.body["traceparent"])


def child_traceparent(parent: str) -> str:
    """Mesmo trace, span novo (os spans OTel reais entram na E7.1)."""
    _, trace_id, _, flags = parent.split("-")
    span_id = secrets.token_hex(8)
    while span_id == "0" * 16:
        span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-{flags}"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class EventFactory:
    def __init__(self, contracts: ContractRegistry) -> None:
        self._contracts = contracts

    def _event(
        self, ctx: TurnContext, message_type: str, idempotency_key: str, payload: dict[str, Any]
    ) -> Event:
        body: dict[str, Any] = {
            "id": str(uuid.uuid7()),
            "type": message_type,
            "occurred_at": _now(),
            "correlation_id": ctx.correlation_id,
            "causation_id": ctx.command_id,
            "idempotency_key": idempotency_key,
            "producer": PRODUCER,
            "traceparent": child_traceparent(ctx.traceparent),
            "payload": payload,
        }
        violations = self._contracts.violations(message_type, body)
        if violations:
            raise InvalidEventError(f"{message_type} não valida: {', '.join(map(str, violations))}")
        return Event(type=message_type, body=body)

    def _turn_ids(self, ctx: TurnContext) -> dict[str, Any]:
        return {
            "user_id": ctx.user_id,
            "conversation_id": ctx.conversation_id,
            "user_message_id": ctx.user_message_id,
            "run_id": ctx.run_id,
        }

    def turn_completed(self, ctx: TurnContext, content: str, finish_reason: FinishReason) -> Event:
        payload = {
            **self._turn_ids(ctx),
            # Gerado aqui para a persistência no Laravel ser idempotente.
            "assistant_message_id": str(uuid.uuid7()),
            "content": content,
            "finish_reason": finish_reason,
        }
        return self._event(ctx, TURN_COMPLETED, f"turn_completed:{ctx.user_message_id}", payload)

    def turn_failed(
        self, ctx: TurnContext, reason: FailReason, code: str, message: str, *, retryable: bool
    ) -> Event:
        payload = {
            **self._turn_ids(ctx),
            "reason": reason,
            "error": {"code": code, "message": message, "retryable": retryable},
        }
        return self._event(ctx, TURN_FAILED, f"turn_failed:{ctx.user_message_id}", payload)

    def usage_recorded(
        self, ctx: TurnContext, provider: Provider, model: str, usage: Usage, cost: Cost, latency_ms: int
    ) -> Event:
        usage_id = str(uuid.uuid7())
        payload: dict[str, Any] = {
            "user_id": ctx.user_id,
            "usage_id": usage_id,
            "conversation_id": ctx.conversation_id,
            "run_id": ctx.run_id,
            "provider": provider,
            "model": model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "cost_usd": format_usd(cost.usd),
            "latency_ms": latency_ms,
        }
        if ctx.mission_id is not None:
            payload["mission_id"] = ctx.mission_id
        return self._event(ctx, USAGE_RECORDED, f"usage:{usage_id}", payload)
