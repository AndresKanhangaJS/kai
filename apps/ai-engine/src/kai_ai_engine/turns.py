"""Turno de conversa (SPEC-004 §3): valida, deduplica, gera e reporta.

Uma mensagem aceite dá exactamente um `turn.completed` ou `turn.failed`, mais um
`usage.recorded` por chamada ao fornecedor com consumo. Só se faz `ack` depois dos confirms.
Nenhum log leva conteúdo: só IDs, códigos e contagens.
"""

import asyncio
import functools
import json
import logging
import math
import random
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from kai_ai_engine.contracts import ContractRegistry, Violation
from kai_ai_engine.events import (
    TURN_COMPLETED,
    TURN_FAILED,
    USAGE_RECORDED,
    Event,
    EventFactory,
    FailReason,
    FinishReason,
    TurnContext,
)
from kai_ai_engine.inbox import Inbox
from kai_ai_engine.llm.errors import LlmError
from kai_ai_engine.llm.gateway import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    LLMGateway,
    Usage,
    UsageMeter,
    generate,
)
from kai_ai_engine.publisher import EventPublisher

log = logging.getLogger(__name__)

API_USER = "kai-api"
TURN_REQUESTED = "ai.conversation.turn.requested.v1"
CANCEL_REQUESTED = "ai.mission.cancel.requested.v1"
STEP_RESUME = "ai.mission.step.resume.v1"
COMMANDS = frozenset({TURN_REQUESTED, CANCEL_REQUESTED, STEP_RESUME})
# O broker limita a 16 MiB (`max_message_size`); acima disto nem se tenta ler.
MAX_BODY_BYTES = 16 * 1024 * 1024
# A chave `processing` dura o turno mais esta margem (depois expira). Uma reentrega que a
# encontre retoma o turno logo: só é seguro com uma réplica do ai-engine (SPEC-004 §6; [P] E10).
INBOX_GRACE_SECONDS = 60
# No shutdown, tempo para publicar o usage da geração interrompida antes do nack.
CANCEL_PUBLISH_SECONDS = 3.0
MAX_CONTENT_CHARS = 100_000
PROMPT_VERSION = "conversation/v1"
PROMPT_FILE = Path(__file__).parent / "prompts" / "conversation" / "v1.md"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
# O mesmo padrão do `model` no usage.recorded.v1 (com fullmatch: sem `\n` final).
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
# Contratos sem os quais o serviço não pode trabalhar: em falta, falha no arranque.
REQUIRED_CONTRACTS = COMMANDS | {TURN_COMPLETED, TURN_FAILED, USAGE_RECORDED}


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


class Delivery(Protocol):
    """O que o handler precisa de uma mensagem AMQP (o `IncomingMessage` do aio-pika cumpre-o)."""

    @property
    def body(self) -> bytes: ...

    @property
    def user_id(self) -> str | None: ...

    @property
    def routing_key(self) -> str | None: ...

    def ack(self) -> Awaitable[None]: ...

    def reject(self, requeue: bool = False) -> Awaitable[None]: ...

    def nack(self, *, requeue: bool = True) -> Awaitable[None]: ...


class InfraError(RuntimeError):
    """Redis ou broker continuam a falhar depois dos retries."""


@dataclass(frozen=True)
class Retry:
    attempts: int
    base_delay: float
    max_delay: float

    def delay(self, attempt: int) -> float:
        """Backoff exponencial com jitter (ADR-0018)."""
        return min(self.max_delay, math.ldexp(self.base_delay, attempt - 1)) * random.uniform(0.5, 1.0)  # noqa: S311


INFRA_RETRY = Retry(attempts=3, base_delay=1.0, max_delay=10.0)
PROVIDER_RETRY = Retry(attempts=5, base_delay=0.5, max_delay=8.0)


@dataclass(frozen=True)
class Rejected:
    reason: str
    message_id: str | None = None
    violations: tuple[Violation, ...] = ()


@dataclass
class TurnResult:
    events: list[Event]
    outcome: str
    reason: str
    attempts: int
    usage_events: int = 0


@dataclass
class _Ledger:
    """Consumo do turno. Vive fora de `_run`: um erro interno ou um shutdown a meio não perdem
    o usage já registado nem o da tentativa em curso."""

    events: list[Event] = field(default_factory=list)
    meter: UsageMeter | None = None
    started: float = 0.0
    # Tecto do que pode já ter sido facturado por tentativas falhadas (o usage parcial pode vir
    # subcontado: o output só chega no fim do stream).
    committed: Decimal = Decimal(0)


class TurnHandler:
    def __init__(
        self,
        *,
        gateway: LLMGateway,
        inbox: Inbox,
        publisher: EventPublisher,
        contracts: ContractRegistry,
        system_prompt: str | None = None,
        infra_retry: Retry = INFRA_RETRY,
        provider_retry: Retry = PROVIDER_RETRY,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._gateway = gateway
        self._inbox = inbox
        self._publisher = publisher
        missing = sorted(t for t in REQUIRED_CONTRACTS if not contracts.knows(t))
        if missing:
            raise RuntimeError(f"contratos em falta: {', '.join(missing)}")
        self._contracts = contracts
        self._events = EventFactory(contracts)
        self._system_prompt = system_prompt if system_prompt is not None else load_system_prompt()
        self._infra_retry = infra_retry
        self._provider_retry = provider_retry
        self._sleep = sleep
        # Reentregas do mesmo id enquanto o original ainda corre neste processo (ex.: canal caiu).
        self._inflight: dict[str, asyncio.Event] = {}

    async def handle(self, delivery: Delivery) -> None:
        received = asyncio.get_running_loop().time()
        decoded = self._decode(delivery)
        if isinstance(decoded, Rejected):
            await self._reject(delivery, decoded)
            return
        message_type, body = decoded
        message_id: str = body["id"]
        if message_type == CANCEL_REQUESTED:
            # Até à E3.5: confirmado sem efeito (o mesmo que para uma missão desconhecida).
            log.info("cancel_ignored", extra={"fields": {"message_id": message_id}})
            await delivery.ack()
            return
        if message_type != TURN_REQUESTED:
            await self._reject(delivery, Rejected("unsupported_type", message_id))
            return
        if body["payload"].get("tools"):
            # Ferramentas só no M05 (SPEC-004 §3.2): nunca se chama o modelo com elas.
            await self._reject(delivery, Rejected("tools_not_supported", message_id))
            return

        while (running := self._inflight.get(message_id)) is not None:
            await running.wait()
        finished = asyncio.Event()
        self._inflight[message_id] = finished
        try:
            await self._process(delivery, body, received)
        finally:
            del self._inflight[message_id]
            finished.set()

    # --- validação ---------------------------------------------------------------------------

    def _decode(self, delivery: Delivery) -> Rejected | tuple[str, dict[str, Any]]:
        # Autenticidade da origem: o broker garante o user_id; exigimos o do produtor.
        if delivery.user_id != API_USER:
            return Rejected("user_id_mismatch")
        if len(delivery.body) > MAX_BODY_BYTES:
            return Rejected("body_too_large")
        try:
            document = json.loads(delivery.body, parse_constant=_reject_constant)
        except ValueError, UnicodeDecodeError:
            return Rejected("invalid_json")
        if not isinstance(document, dict) or not isinstance(document.get("type"), str):
            return Rejected("invalid_envelope")
        raw_id = document.get("id")
        message_id = raw_id if isinstance(raw_id, str) and UUID_RE.fullmatch(raw_id) else None
        message_type: str = document["type"]
        if message_type not in COMMANDS or not self._contracts.knows(message_type):
            return Rejected("unsupported_type", message_id)
        violations = self._contracts.violations(message_type, document)
        if violations:
            return Rejected("schema", message_id, tuple(violations))
        if delivery.routing_key != message_type:
            return Rejected("routing_key_mismatch", message_id)
        # As patterns dos schemas aceitam um `\n` final (o `$` do Python); nos identificadores
        # isso mudaria a chave da inbox e partiria os eventos.
        if message_id is None or any("\n" in v for v in _identifiers(document)):
            return Rejected("invalid_id", message_id)
        return message_type, document

    async def _reject(self, delivery: Delivery, rejected: Rejected) -> None:
        log.warning(
            "message_rejected",
            extra={
                "fields": {
                    "reason": rejected.reason,
                    "message_id": rejected.message_id,
                    "violations": [str(v) for v in rejected.violations[:10]],
                }
            },
        )
        # Sem requeue: o DLX leva-a para a DLQ (ADR-0018).
        await delivery.reject(requeue=False)

    # --- processamento -----------------------------------------------------------------------

    async def _process(self, delivery: Delivery, body: dict[str, Any], received: float) -> None:
        message_id: str = body["id"]
        payload: dict[str, Any] = body["payload"]
        ttl = int(payload["limits"]["timeout_seconds"]) + INBOX_GRACE_SECONDS
        try:
            state = await self._infra("inbox_claim", lambda: self._inbox.claim(message_id, ttl))
        except InfraError:
            # Nada foi gasto: volta à fila (o x-delivery-limit acaba por a levar para a DLQ).
            fields = {"reason": "inbox_unavailable", "message_id": message_id}
            log.warning("message_requeued", extra={"fields": fields})
            await delivery.nack(requeue=True)
            return
        if state == "done":
            log.info("inbox_duplicate", extra={"fields": {"message_id": message_id}})
            await delivery.ack()
            return
        if state == "processing":
            # Rasto de um processamento interrompido (crash ou shutdown a meio): retoma-se.
            log.warning("inbox_takeover", extra={"fields": {"message_id": message_id}})

        ctx = TurnContext(
            command_id=message_id,
            correlation_id=body["correlation_id"],
            traceparent=body["traceparent"],
            user_id=int(payload["user_id"]),
            conversation_id=payload["conversation_id"],
            user_message_id=payload["user_message_id"],
            run_id=payload["run_id"],
            mission_id=payload.get("mission_id"),
        )
        log.info(
            "turn_started",
            extra={
                "fields": {
                    "message_id": message_id,
                    "run_id": ctx.run_id,
                    "user_id": ctx.user_id,
                    "provider": self._gateway.provider,
                    "model": self._gateway.model,
                    "prompt_version": PROMPT_VERSION,
                }
            },
        )
        ledger = _Ledger()
        try:
            result = await self._run(ctx, payload, received, ledger)
        except asyncio.CancelledError:
            # Shutdown a meio: o fornecedor já facturou o que gerou. Publica o usage antes de a
            # mensagem voltar à fila (o consumidor faz o nack).
            await self._publish_usage_on_cancel(ctx, ledger, message_id)
            raise
        except Exception:
            # Bug nosso (ex.: evento que não valida): reporta sem detalhes, se for possível.
            log.exception("turn_internal_error", extra={"fields": {"message_id": message_id}})
            try:
                self._close_attempt(ctx, ledger)
                failure = self._events.turn_failed(
                    ctx, "internal_error", "internal_error", "erro interno do AI Engine", retryable=True
                )
            except Exception:
                await self._reject(delivery, Rejected("internal_error", message_id))
                return
            # Os usage já registados saem sempre: a chamada custou.
            result = TurnResult([*ledger.events, failure], "failed", "internal_error", 0, len(ledger.events))

        try:
            for event in result.events:
                await self._infra("publish", functools.partial(self._publisher.publish, event))
        except InfraError:
            # Sem confirms não há ack: a mensagem vai para a DLQ e o produtor reemite (ADR-0018).
            await self._reject(delivery, Rejected("publish_failed", message_id))
            return
        try:
            await self._infra("inbox_done", lambda: self._inbox.mark_done(message_id))
        except InfraError:
            # Os eventos já saíram: confirma na mesma (o Laravel deduplica pela idempotency_key).
            log.warning("inbox_mark_failed", extra={"fields": {"message_id": message_id}})
        await delivery.ack()
        log.info(
            "turn_finished",
            extra={
                "fields": {
                    "message_id": message_id,
                    "run_id": ctx.run_id,
                    "outcome": result.outcome,
                    "reason": result.reason,
                    "attempts": result.attempts,
                    "usage_events": result.usage_events,
                    "latency_ms": int((asyncio.get_running_loop().time() - received) * 1000),
                }
            },
        )

    async def _run(
        self, ctx: TurnContext, payload: dict[str, Any], received: float, ledger: _Ledger
    ) -> TurnResult:
        loop = asyncio.get_running_loop()
        limits: dict[str, Any] = payload["limits"]
        deadline = received + int(limits["timeout_seconds"])
        max_output_tokens = int(limits["max_output_tokens"])
        max_cost = Decimal(limits["max_cost_usd"])
        # As mensagens do owner entram como `user`, nunca como instruções de sistema (§3.8).
        messages = tuple(ChatMessage(role=m["role"], content=m["content"]) for m in payload["messages"])
        attempts = 0
        last_error: LlmError | None = None

        def request() -> GenerationRequest:
            return GenerationRequest(
                model=self._gateway.model,
                messages=messages,
                max_output_tokens=max_output_tokens,
                timeout_seconds=max(0.001, deadline - loop.time()),
                system=self._system_prompt,
            )

        def failed(reason: FailReason, code: str, message: str, retryable: bool) -> TurnResult:
            event = self._events.turn_failed(ctx, reason, code, message, retryable=retryable)
            return TurnResult([*ledger.events, event], "failed", reason, attempts, len(ledger.events))

        try:
            async with asyncio.timeout_at(deadline):
                # Orçamento antes de qualquer geração (AC-004-07).
                count_attempt = 0
                while True:
                    count_attempt += 1
                    try:
                        input_tokens = await self._gateway.count_tokens(request())
                        break
                    except LlmError as exc:
                        if not await self._backoff(exc, count_attempt, deadline):
                            return failed(*_llm_failure(exc))
                worst = self._gateway.estimate_max_cost(input_tokens, max_output_tokens)
                if worst > max_cost:
                    return failed(
                        "budget_exceeded",
                        "budget_exceeded",
                        "o custo máximo estimado excede o orçamento do turno",
                        retryable=False,
                    )

                while True:
                    # Cada tentativa tem de caber no que sobra do orçamento (revisão da E3.4a).
                    if last_error is not None and ledger.committed + worst > max_cost:
                        log.info("llm_retry_over_budget", extra={"fields": {"attempt": attempts}})
                        return failed(*_llm_failure(last_error))
                    attempts += 1
                    ledger.meter, ledger.started = UsageMeter(), loop.time()
                    try:
                        result = await generate(self._gateway, request(), ledger.meter)
                    except LlmError as exc:
                        if _billed(ledger.meter):
                            ledger.committed += worst
                        self._close_attempt(ctx, ledger)
                        last_error = exc
                        # Retry só antes do primeiro delta e dentro do prazo (AC-004-09).
                        fits = ledger.committed + worst <= max_cost
                        if fits and await self._backoff(exc, attempts, deadline):
                            continue
                        return failed(*_llm_failure(exc))
                    ledger.meter = None
                    self._record(ctx, ledger, result.completed.usage, result.completed.model)
                    return self._finish(ctx, result, ledger, attempts)
        except TimeoutError:
            # O fornecedor factura o que já gerou (AC-004-06).
            self._close_attempt(ctx, ledger)
            return failed("timeout", "turn_timeout", "o turno excedeu o tempo limite", retryable=True)

    def _record(self, ctx: TurnContext, ledger: _Ledger, usage: Usage, model: str | None = None) -> None:
        if usage.input_tokens + usage.output_tokens + usage.cache_read_tokens + usage.cache_write_tokens == 0:
            return
        reported = model or (usage.by_model[-1].model if usage.by_model else "")
        if not MODEL_RE.fullmatch(reported):
            # Nome do fornecedor fora do contrato: nunca perder o usage por isso.
            reported = self._gateway.model
        ledger.events.append(
            self._events.usage_recorded(
                ctx,
                self._gateway.provider,
                reported,
                usage,
                self._gateway.cost(usage),
                int((asyncio.get_running_loop().time() - ledger.started) * 1000),
            )
        )

    def _close_attempt(self, ctx: TurnContext, ledger: _Ledger) -> None:
        """Regista o consumo da tentativa em curso (interrompida), se houver."""
        meter, ledger.meter = ledger.meter, None
        if meter is not None:
            self._record(ctx, ledger, meter.snapshot())

    async def _publish_usage_on_cancel(self, ctx: TurnContext, ledger: _Ledger, message_id: str) -> None:
        try:
            self._close_attempt(ctx, ledger)

            async def publish_all() -> None:
                for event in ledger.events:
                    await self._publisher.publish(event)

            if ledger.events:
                await asyncio.wait_for(asyncio.shield(publish_all()), CANCEL_PUBLISH_SECONDS)
        except Exception as exc:
            log.warning(
                "usage_lost_on_shutdown",
                extra={"fields": {"message_id": message_id, "error_class": type(exc).__name__}},
            )

    async def _backoff(self, exc: LlmError, attempt: int, deadline: float) -> bool:
        if not exc.retryable or exc.after_first_delta or attempt >= self._provider_retry.attempts:
            return False
        delay = self._provider_retry.delay(attempt)
        if asyncio.get_running_loop().time() + delay >= deadline:
            return False
        log.info("llm_retry", extra={"fields": {"attempt": attempt, "code": exc.code}})
        await self._sleep(delay)
        return True

    def _finish(
        self, ctx: TurnContext, result: GenerationResult, usages: _Ledger, attempts: int
    ) -> TurnResult:
        stop = result.completed.stop_reason
        problem: tuple[str, str] | None = None
        finish: FinishReason = "end_turn"
        if stop == "refusal":
            problem = ("model_refusal", "o modelo recusou responder")
        elif stop == "other":
            problem = ("unexpected_stop", "o fornecedor terminou de forma inesperada")
        elif not result.text.strip():
            problem = ("empty_response", "o fornecedor devolveu uma resposta vazia")
        elif len(result.text) > MAX_CONTENT_CHARS:
            problem = ("response_too_long", "a resposta excede o tamanho máximo")
        elif stop == "max_tokens":
            finish = "max_output_tokens"
        if problem is not None:
            event = self._events.turn_failed(ctx, "provider_error", *problem, retryable=False)
            return TurnResult(
                [*usages.events, event], "failed", "provider_error", attempts, len(usages.events)
            )
        completed = self._events.turn_completed(ctx, result.text, finish)
        return TurnResult([*usages.events, completed], "completed", finish, attempts, len(usages.events))

    async def _infra[T](self, operation: str, action: Callable[[], Awaitable[T]]) -> T:
        for attempt in range(1, self._infra_retry.attempts + 1):
            try:
                return await action()
            except Exception as exc:
                log.warning(
                    "infra_retry",
                    extra={
                        "fields": {
                            "operation": operation,
                            "attempt": attempt,
                            "error_class": type(exc).__name__,
                        }
                    },
                )
                if attempt < self._infra_retry.attempts:
                    await self._sleep(self._infra_retry.delay(attempt))
        raise InfraError(operation)


def _llm_failure(exc: LlmError) -> tuple[FailReason, str, str, bool]:
    """Motivo, código, mensagem segura (a do adaptador nunca leva conteúdo do fornecedor) e se o
    owner pode repetir o turno mais tarde."""
    if exc.code == "provider_timeout":
        return "timeout", exc.code, exc.message, True
    if exc.retryable and not exc.after_first_delta:
        return "provider_unavailable", exc.code, exc.message, True
    return "provider_error", exc.code, exc.message, exc.retryable


def _billed(meter: UsageMeter) -> bool:
    """O fornecedor já respondeu (e factura), mesmo sem texto: raciocínio também é output."""
    return bool(meter.input_tokens or meter.output_tokens or meter.deltas or meter.iterations)


def _identifiers(document: dict[str, Any]) -> list[str]:
    payload = document.get("payload") or {}
    values = [document.get(k) for k in ("id", "correlation_id", "idempotency_key", "traceparent")]
    values += [payload.get(k) for k in ("conversation_id", "user_message_id", "run_id", "mission_id")]
    return [v for v in values if isinstance(v, str)]


def _reject_constant(name: str) -> None:
    raise ValueError("NaN e Infinity não são JSON válido")
