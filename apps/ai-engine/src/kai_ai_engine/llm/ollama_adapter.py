"""Adaptador Ollama (ADR-0006, D-08): API nativa `/api/chat` em streaming NDJSON, sobre `httpx2`.

O URL é configuração do owner (`OLLAMA_HOST`), nunca vem da mensagem. Custo 0; a contagem de
tokens antes da chamada é só uma estimativa conservadora (`exact_token_count=False`).
"""

import ipaddress
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlsplit

import httpx2

from kai_ai_engine.llm.errors import LlmError, ProviderError, ProviderUnavailableError, detached
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

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 5.0
# Estimativa por excesso: ~1 token por cada 3 caracteres, mais 4 por mensagem.
CHARS_PER_TOKEN = 3
TOKENS_PER_MESSAGE = 4
# http em claro só dentro da máquina ou da rede privada; fora dela, https.
LOCAL_HOSTNAMES = frozenset({"localhost", "host.docker.internal"})


class OllamaConfigError(ValueError):
    """OLLAMA_HOST inválido; a mensagem nunca leva o valor."""


@dataclass(frozen=True)
class OllamaSettings:
    host: str
    model: str

    def __post_init__(self) -> None:
        parts = urlsplit(self.host)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise OllamaConfigError("OLLAMA_HOST tem de ser um URL http(s) com host")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise OllamaConfigError("OLLAMA_HOST não pode ter credenciais, query nem fragmento")
        if parts.scheme == "http" and not _is_local(parts.hostname):
            raise OllamaConfigError("OLLAMA_HOST fora da rede local tem de usar https")


class OllamaGateway:
    def __init__(self, settings: OllamaSettings, http_client: httpx2.AsyncClient | None = None) -> None:
        self._settings = settings
        # Sem redirects nem proxies do ambiente: os prompts só vão para o OLLAMA_HOST.
        self._client = http_client or httpx2.AsyncClient(follow_redirects=False, trust_env=False)
        self._url = settings.host.rstrip("/") + "/api/chat"

    @property
    def provider(self) -> Provider:
        return "ollama"

    @property
    def model(self) -> str:
        return self._settings.model

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, exact_token_count=False, priced=False)

    def estimate_max_cost(self, input_tokens: int, max_output_tokens: int) -> Decimal:
        return Decimal(0)

    def cost(self, usage: Usage) -> Cost:
        return Cost(usd=Decimal(0))

    async def count_tokens(self, request: GenerationRequest) -> int:
        texts = [request.system or "", *(m.content for m in request.messages)]
        return sum(-(-len(t) // CHARS_PER_TOKEN) + TOKENS_PER_MESSAGE for t in texts)

    async def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        if request.model != self._settings.model:
            raise ProviderError("model_not_allowed", "modelo não configurado")
        meter = meter if meter is not None else UsageMeter()
        meter.model = request.model
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        if request.system is not None:
            messages.insert(0, {"role": "system", "content": request.system})
        body = {
            "model": request.model,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": request.max_output_tokens},
        }
        timeout = httpx2.Timeout(request.timeout_seconds, connect=CONNECT_TIMEOUT_SECONDS)
        started = time.monotonic()
        deadline = started + request.timeout_seconds
        last: dict[str, object] | None = None
        error: LlmError | None = None
        try:
            async with self._client.stream("POST", self._url, json=body, timeout=timeout) as response:
                if response.status_code != 200:
                    error = _status_error(response.status_code)
                else:
                    async for line in response.aiter_lines():
                        if time.monotonic() > deadline:
                            error = ProviderUnavailableError(
                                "provider_timeout", "o fornecedor excedeu o prazo"
                            )
                            break
                        if not line.strip():
                            continue
                        chunk = _parse(line)
                        if chunk is None or "error" in chunk:
                            # Erro a meio do stream: o texto do Ollama não sai daqui.
                            error = ProviderError("provider_error", "o fornecedor devolveu um erro")
                            break
                        message = chunk.get("message")
                        if isinstance(message, dict):
                            text = message.get("content")
                            if isinstance(text, str) and text:
                                meter.deltas += 1
                                meter.output_tokens += 1
                                yield TextDelta(text)
                        if chunk.get("done") is True:
                            last = chunk
                            break
        except httpx2.TimeoutException:
            error = ProviderUnavailableError("provider_timeout", "o fornecedor não respondeu a tempo")
        except httpx2.HTTPError:
            error = ProviderUnavailableError("provider_unavailable", "falha de ligação ao fornecedor")

        if error is not None or last is None:
            error = error or ProviderUnavailableError(
                "provider_unavailable", "o stream terminou antes do fim"
            )
            log.warning(
                "llm_provider_error",
                extra={"fields": {"provider": "ollama", "code": error.code, "status": error.status}},
            )
            # Fora do `except`: sem a excepção do httpx2 encadeada.
            raise detached(error, after_first_delta=meter.deltas > 0)

        usage = Usage(
            by_model=(
                ModelUsage(
                    model=request.model,
                    input_tokens=_count(last.get("prompt_eval_count")),
                    output_tokens=_count(last.get("eval_count")),
                ),
            )
        )
        meter.iterations = usage.by_model
        completed = Completed(model=request.model, usage=usage, stop_reason=_stop(last.get("done_reason")))
        log.info(
            "llm_stream_completed",
            extra={
                "fields": {
                    "provider": "ollama",
                    "model": request.model,
                    "stop_reason": completed.stop_reason,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "latency_ms": int((time.monotonic() - started) * 1000),
                }
            },
        )
        yield completed

    async def aclose(self) -> None:
        await self._client.aclose()


def _parse(line: str) -> dict[str, object] | None:
    try:
        value = json.loads(line)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _status_error(status: int) -> LlmError:
    if status in (408, 429) or status >= 500:
        return ProviderUnavailableError("provider_unavailable", "fornecedor indisponível", status=status)
    return ProviderError("provider_rejected", "o fornecedor recusou o pedido", status=status)


def _count(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _stop(reason: object) -> StopReason:
    if reason == "stop":
        return "end_turn"
    if reason == "length":
        return "max_tokens"
    return "other"


def _is_local(hostname: str) -> bool:
    if hostname in LOCAL_HOSTNAMES or "." not in hostname:
        # Sem ponto: nome de serviço do Compose, só resolúvel na rede interna.
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_private
