"""Fornecedor `fake` (P-015, AC-10): determinístico, sem rede, por omissão.

Configurável para os testes de integração da E3.4: atraso por delta (AC-004-06), falhas
transitórias antes ou depois do primeiro delta (AC-004-09) e resposta fixa (canário, AC-004-11).
"""

import asyncio
import math
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass

from kai_ai_engine.llm.errors import ProviderUnavailableError, detached
from kai_ai_engine.llm.gateway import (
    Capabilities,
    Completed,
    GenerationRequest,
    ModelUsage,
    Provider,
    StreamEvent,
    TextDelta,
    Usage,
    UsageMeter,
)

FAKE_MODEL = "fake-echo-1"
PREFIX = "Resposta fake: "


class FakeConfigError(ValueError):
    """Variável KAI_FAKE_* inválida; a mensagem nomeia a variável, nunca o valor."""


@dataclass(frozen=True)
class FakeOptions:
    delay_per_delta: float = 0.0
    words_per_delta: int = 2
    # Falha transitória nas primeiras N chamadas, antes de qualquer delta.
    fail_before_first_delta: int = 0
    # Falha transitória depois de emitir este número de deltas (None: nunca).
    fail_after_deltas: int | None = None
    # Resposta fixa; por omissão é um eco determinístico da última mensagem.
    script: str | None = None


def options_from_env(env: Mapping[str, str]) -> FakeOptions:
    def number(name: str, default: str, kind: type[int] | type[float]) -> float:
        raw = env.get(name, default)
        try:
            value = kind(raw)
        except ValueError:
            raise FakeConfigError(f"{name} tem de ser um número") from None
        if not math.isfinite(value) or value < 0:
            raise FakeConfigError(f"{name} tem de ser finito e não negativo")
        return value

    after = env.get("KAI_FAKE_FAIL_AFTER_DELTAS")
    return FakeOptions(
        delay_per_delta=number("KAI_FAKE_DELAY_PER_DELTA", "0", float),
        words_per_delta=max(1, int(number("KAI_FAKE_WORDS_PER_DELTA", "2", int))),
        fail_before_first_delta=int(number("KAI_FAKE_FAIL_BEFORE_FIRST_DELTA", "0", int)),
        fail_after_deltas=None if after is None else int(number("KAI_FAKE_FAIL_AFTER_DELTAS", after, int)),
        script=env.get("KAI_FAKE_SCRIPT") or None,
    )


class FakeGateway:
    def __init__(self, options: FakeOptions | None = None) -> None:
        self._options = options or FakeOptions()
        self._calls = 0

    @property
    def provider(self) -> Provider:
        return "fake"

    @property
    def calls(self) -> int:
        """Chamadas a `stream` (os testes verificam que não houve chamada ao fornecedor)."""
        return self._calls

    def capabilities(self) -> Capabilities:
        return Capabilities(streaming=True, exact_token_count=True, priced=False)

    async def count_tokens(self, request: GenerationRequest) -> int:
        return _words(request.system or "") + sum(_words(m.content) for m in request.messages)

    def response_for(self, request: GenerationRequest) -> str:
        if self._options.script is not None:
            return self._options.script
        return PREFIX + request.messages[-1].content

    async def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        self._calls += 1
        opts = self._options
        meter = meter if meter is not None else UsageMeter()
        meter.model = FAKE_MODEL
        if self._calls <= opts.fail_before_first_delta:
            raise detached(
                ProviderUnavailableError("provider_unavailable", "falha transitória injectada (fake)"),
                after_first_delta=False,
            )
        meter.input_tokens = await self.count_tokens(request)

        words = self.response_for(request).split(" ")
        # Respeita o max_output_tokens (1 palavra = 1 token no fake).
        truncated = len(words) > request.max_output_tokens
        words = words[: request.max_output_tokens]
        chunks = [
            " ".join(words[i : i + opts.words_per_delta]) for i in range(0, len(words), opts.words_per_delta)
        ]
        for index, chunk in enumerate(chunks):
            if opts.fail_after_deltas is not None and index == opts.fail_after_deltas:
                raise detached(
                    ProviderUnavailableError("provider_unavailable", "falha transitória injectada (fake)"),
                    after_first_delta=meter.deltas > 0,
                )
            if opts.delay_per_delta:
                await asyncio.sleep(opts.delay_per_delta)
            meter.deltas += 1
            meter.output_tokens += len(chunk.split(" "))
            yield TextDelta(chunk if index == 0 else " " + chunk)

        usage = Usage(
            by_model=(
                ModelUsage(model=FAKE_MODEL, input_tokens=meter.input_tokens, output_tokens=len(words)),
            )
        )
        yield Completed(model=FAKE_MODEL, usage=usage, stop_reason="max_tokens" if truncated else "end_turn")

    async def aclose(self) -> None:
        return None


def _words(text: str) -> int:
    return len(text.split())
