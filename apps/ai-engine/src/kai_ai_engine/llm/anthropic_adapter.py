"""Adaptador Anthropic (ADR-0006, D-08) sobre o SDK oficial `anthropic`, assíncrono.

- O SDK não repete (`max_retries=0`): o retry é do consumidor, só antes do primeiro delta e
  dentro do timeout do turno (AC-004-09, ADR-0018).
- A chave é passada explicitamente: o SDK nunca vai buscar perfis nem outros tokens.
- Fallback de recusa do lado do servidor, com modelos fixos (todos com preço na tabela).
- Nenhuma mensagem ou corpo do fornecedor sai daqui: os erros levam só código e status, sem a
  excepção original encadeada (que guarda o pedido, com a chave, e o corpo).
- O cliente HTTP ignora proxies e certificados do ambiente (`trust_env=False`).
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import anthropic
import httpx2
import pydantic
from anthropic.types.beta import (
    BetaAssistantMessageParam,
    BetaMessage,
    BetaMessageParam,
    BetaUserMessageParam,
)

from kai_ai_engine.llm.errors import (
    LlmError,
    PricingError,
    ProviderError,
    ProviderUnavailableError,
    detached,
)
from kai_ai_engine.llm.gateway import (
    Capabilities,
    Completed,
    Cost,
    GenerationRequest,
    ModelUsage,
    Provider,
    StopReason,
    StreamEvent,
    TextDelta,
    Usage,
    UsageMeter,
)
from kai_ai_engine.llm.pricing import PriceTable, load_price_table

log = logging.getLogger(__name__)

API_BASE_URL = "https://api.anthropic.com"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
CONNECT_TIMEOUT_SECONDS = 5.0
# 408/409/429 e >= 500 (inclui 529 overloaded): transitórios, como no próprio SDK.
TRANSIENT_STATUS = frozenset({408, 409, 429})
TRANSIENT_TYPES = frozenset({"overloaded_error", "rate_limit_error", "api_error"})
# Falhas do fornecedor ou do transporte, incluindo a meio do stream (JSON malformado no SSE).
PROVIDER_FAILURES = (
    anthropic.AnthropicError,
    httpx2.HTTPError,
    pydantic.ValidationError,
    json.JSONDecodeError,
)
# Geografias sem prémio; qualquer outra (ex.: "us", x1,1) é um modificador de preço.
STANDARD_GEOS = frozenset({"global", "not_available"})

Effort = Literal["low", "medium", "high", "xhigh", "max"]


@dataclass(frozen=True)
class AnthropicSettings:
    # repr=False: a chave nunca aparece em logs, tracebacks nem no repr.
    api_key: str = field(repr=False)
    model: str = "claude-opus-5-5"
    effort: Effort = "medium"
    fallback_models: tuple[str, ...] = ("claude-opus-5",)


class AnthropicGateway:
    def __init__(
        self,
        settings: AnthropicSettings,
        http_client: httpx2.AsyncClient | None = None,
        prices: PriceTable | None = None,
    ) -> None:
        self._settings = settings
        self._prices = prices or load_price_table()
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.api_key,
            base_url=API_BASE_URL,
            max_retries=0,
            http_client=http_client or anthropic.DefaultAsyncHttpxClient(trust_env=False),
            # Sem os spans do próprio SDK (podem levar prompts e respostas no modo "content");
            # os spans `llm.generate` do KAI, só com metadados, entram na E7.1.
            open_telemetry=False,
        )

    @property
    def provider(self) -> Provider:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._settings.model

    @property
    def possible_models(self) -> tuple[str, ...]:
        """Modelos que podem servir o pedido; o orçamento soma a cadeia inteira."""
        return (self._settings.model, *self._settings.fallback_models)

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, exact_token_count=True, priced=True)

    def estimate_max_cost(self, input_tokens: int, max_output_tokens: int) -> Decimal:
        return self._prices.estimate_max_cost(self.possible_models, input_tokens, max_output_tokens)

    def cost(self, usage: Usage) -> Cost:
        try:
            return Cost(usd=self._prices.cost(usage))
        except PricingError as exc:
            # A chamada já custou: regista-se por cima, nunca 0 nem uma falha (AC-004-06).
            log.warning(
                "llm_cost_conservative",
                extra={"fields": {"provider": "anthropic", "code": exc.code, "prices": self._prices.version}},
            )
            return Cost(usd=self._prices.cost_conservative(usage), exact=False)

    def _timeout(self, request: GenerationRequest) -> anthropic.Timeout:
        return anthropic.Timeout(request.timeout_seconds, connect=CONNECT_TIMEOUT_SECONDS)

    def _check_model(self, request: GenerationRequest) -> None:
        # Defesa em profundidade: o modelo vem da configuração, validada contra a tabela de preços.
        if request.model != self._settings.model:
            raise ProviderError("model_not_allowed", "modelo não configurado")

    async def count_tokens(self, request: GenerationRequest) -> int:
        self._check_model(request)
        error: LlmError | None = None
        try:
            client = self._client.with_options(timeout=self._timeout(request))
            result = await client.beta.messages.count_tokens(
                model=request.model,
                messages=_messages(request),
                system=request.system if request.system is not None else anthropic.omit,
            )
        except PROVIDER_FAILURES as exc:
            error = _map_error(exc)
        if error is not None:
            # Levantado fora do `except`: assim o Python não volta a encadear o erro do SDK.
            raise detached(error, after_first_delta=False)
        return result.input_tokens

    async def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        self._check_model(request)
        meter = meter if meter is not None else UsageMeter()
        started = time.monotonic()
        deadline = started + request.timeout_seconds
        final: BetaMessage | None = None
        error: LlmError | None = None
        try:
            async with self._client.with_options(timeout=self._timeout(request)).beta.messages.stream(
                model=request.model,
                max_tokens=request.max_output_tokens,
                messages=_messages(request),
                system=request.system if request.system is not None else anthropic.omit,
                # Sem `thinking`: no Opus 5.5 corre adaptativo e não se desliga; o esforço controla-o.
                output_config={"effort": self._settings.effort},
                fallbacks=[{"model": m} for m in self._settings.fallback_models] or anthropic.omit,
                betas=[FALLBACK_BETA] if self._settings.fallback_models else anthropic.omit,
            ) as stream:
                async for event in stream:
                    _meter(meter, event, request.model)
                    if time.monotonic() > deadline:
                        # Prazo total: um fornecedor que pinga devagar não estica o turno.
                        error = ProviderUnavailableError("provider_timeout", "o fornecedor excedeu o prazo")
                        break
                    # Só texto: blocos de thinking e de fallback não chegam ao owner. Num fallback a
                    # meio, o texto parcial mantém-se e o fallback continua-o (semântica da API).
                    if event.type == "content_block_delta" and event.delta.type == "text_delta":
                        meter.deltas += 1
                        yield TextDelta(event.delta.text)
                if error is None:
                    final = await stream.get_final_message()
        except PROVIDER_FAILURES as exc:
            error = _map_error(exc)

        if error is not None or final is None:
            error = error or ProviderError("provider_error", "o stream terminou sem resposta final")
            log.warning(
                "llm_provider_error",
                extra={
                    "fields": {
                        "provider": "anthropic",
                        "code": error.code,
                        "status": error.status,
                        "after_first_delta": meter.deltas > 0,
                        "output_tokens": meter.output_tokens,
                    }
                },
            )
            raise detached(error, after_first_delta=meter.deltas > 0)

        completed = _completed(final, request.model)
        meter.iterations = completed.usage.by_model
        if completed.usage.modifiers:
            log.warning(
                "llm_price_modifier",
                extra={"fields": {"provider": "anthropic", "modifiers": sorted(completed.usage.modifiers)}},
            )
        log.info(
            "llm_stream_completed",
            extra={
                "fields": {
                    "provider": "anthropic",
                    "model": completed.model,
                    "stop_reason": completed.stop_reason,
                    "input_tokens": completed.usage.input_tokens,
                    "output_tokens": completed.usage.output_tokens,
                    "attempts": len(completed.usage.by_model),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                }
            },
        )
        yield completed

    async def aclose(self) -> None:
        await self._client.close()


def _messages(request: GenerationRequest) -> list[BetaMessageParam]:
    out: list[BetaMessageParam] = []
    for m in request.messages:
        if m.role == "user":
            out.append(BetaUserMessageParam(role="user", content=m.content))
        else:
            out.append(BetaAssistantMessageParam(role="assistant", content=m.content))
    return out


def _meter(meter: UsageMeter, event: object, requested: str) -> None:
    """Acumula o consumo à medida que chega (o fornecedor factura mesmo sem `Completed`)."""
    kind = getattr(event, "type", None)
    if kind == "message_start":
        message = getattr(event, "message", None)
        usage = getattr(message, "usage", None)
        meter.model = getattr(message, "model", None) or requested
        if usage is not None:
            meter.input_tokens = usage.input_tokens or 0
            meter.output_tokens = usage.output_tokens or 0
            meter.cache_read_tokens = usage.cache_read_input_tokens or 0
            meter.cache_write_tokens = usage.cache_creation_input_tokens or 0
    elif kind == "message_delta":
        usage = getattr(event, "usage", None)
        if usage is not None:
            # As contagens do message_delta são cumulativas.
            meter.output_tokens = max(meter.output_tokens, usage.output_tokens or 0)
            meter.input_tokens = max(meter.input_tokens, usage.input_tokens or 0)
            if usage.iterations:
                meter.iterations = tuple(_iteration(it, requested, meter.model) for it in usage.iterations)


def _iteration(it: object, requested: str, final_model: str) -> ModelUsage:
    model = getattr(it, "model", None)
    if not model:
        # Sem modelo: a tentativa "message" é a do modelo pedido; as outras, a do modelo final.
        model = requested if getattr(it, "type", None) == "message" else final_model
    return ModelUsage(
        model=model,
        input_tokens=getattr(it, "input_tokens", 0) or 0,
        output_tokens=getattr(it, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(it, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(it, "cache_creation_input_tokens", 0) or 0,
    )


def _completed(message: BetaMessage, requested: str) -> Completed:
    usage = message.usage
    # `usage.iterations` é a fonte de verdade por tentativa; o topo cobre só a última.
    by_model = [_iteration(it, requested, message.model) for it in usage.iterations or []]
    if not by_model:
        by_model.append(
            ModelUsage(
                model=message.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_input_tokens or 0,
                cache_write_tokens=usage.cache_creation_input_tokens or 0,
            )
        )
    modifiers: set[str] = set()
    if usage.inference_geo and usage.inference_geo not in STANDARD_GEOS:
        modifiers.add("inference_geo")
    if usage.speed == "fast":
        modifiers.add("fast_mode")
    if usage.cache_creation is not None and usage.cache_creation.ephemeral_1h_input_tokens:
        modifiers.add("cache_1h")
    return Completed(
        model=message.model,
        usage=Usage(by_model=tuple(by_model), modifiers=frozenset(modifiers)),
        stop_reason=_stop(message),
    )


def _stop(message: BetaMessage) -> StopReason:
    match message.stop_reason:
        case "end_turn" | "stop_sequence":
            return "end_turn"
        case "max_tokens" | "model_context_window_exceeded":
            return "max_tokens"
        case "refusal":
            # Toda a cadeia (modelo + fallbacks) recusou. O texto parcial já foi emitido: o
            # consumidor trata o turno como falhado e o cliente descarta-o (E3.4).
            return "refusal"
        case _:
            return "other"


def _map_error(exc: Exception) -> LlmError:
    """Classifica sem copiar a mensagem do fornecedor (pode ecoar o pedido)."""
    if isinstance(exc, (anthropic.APITimeoutError, httpx2.TimeoutException)):
        return ProviderUnavailableError("provider_timeout", "o fornecedor não respondeu a tempo")
    if isinstance(exc, (anthropic.APIConnectionError, httpx2.TransportError)):
        return ProviderUnavailableError("provider_unavailable", "falha de ligação ao fornecedor")
    if isinstance(exc, anthropic.APIStatusError):
        status = exc.status_code
        if status in TRANSIENT_STATUS or status >= 500 or getattr(exc, "type", None) in TRANSIENT_TYPES:
            return ProviderUnavailableError("provider_unavailable", "fornecedor indisponível", status=status)
        return ProviderError("provider_rejected", "o fornecedor recusou o pedido", status=status)
    return ProviderError("provider_error", "resposta inválida do fornecedor")
