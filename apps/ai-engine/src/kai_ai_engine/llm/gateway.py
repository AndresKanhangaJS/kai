"""Porta `LLMGateway` (ADR-0006): tipos canónicos, independentes do fornecedor.

Sem ferramentas no M03 (SPEC-004 §6): um pedido não tem `tools`, e nenhum adaptador as envia.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol

Provider = Literal["anthropic", "ollama", "fake"]
Role = Literal["user", "assistant"]
StopReason = Literal["end_turn", "max_tokens", "refusal", "other"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    # repr=False: o conteúdo nunca aparece num repr ou traceback; os adaptadores não o registam.
    content: str = field(repr=False)


@dataclass(frozen=True)
class GenerationRequest:
    model: str
    messages: tuple[ChatMessage, ...]
    max_output_tokens: int
    timeout_seconds: float
    system: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class ModelUsage:
    """Consumo de uma tentativa, no modelo que a correu (o fallback tem preço próprio)."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class Usage:
    """Consumo do pedido inteiro: uma entrada por tentativa (`usage.iterations`)."""

    by_model: tuple[ModelUsage, ...]
    # Modificadores de preço que a tabela não cobre (geografia, fast mode, cache de 1 h).
    modifiers: frozenset[str] = frozenset()

    @property
    def input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.by_model)

    @property
    def output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.by_model)

    @property
    def cache_read_tokens(self) -> int:
        return sum(u.cache_read_tokens for u in self.by_model)

    @property
    def cache_write_tokens(self) -> int:
        return sum(u.cache_write_tokens for u in self.by_model)


@dataclass
class UsageMeter:
    """Consumo acumulado durante o stream, legível mesmo se o stream for interrompido.

    Um timeout, um cancelamento ou um erro a meio não chegam ao `Completed`, mas o
    fornecedor factura o que já consumiu: o consumidor lê `snapshot()` e regista-o (AC-004-06).
    """

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    iterations: tuple[ModelUsage, ...] = ()
    deltas: int = 0

    def snapshot(self) -> Usage:
        if self.iterations:
            return Usage(by_model=self.iterations)
        return Usage(
            by_model=(
                ModelUsage(
                    model=self.model,
                    input_tokens=self.input_tokens,
                    output_tokens=self.output_tokens,
                    cache_read_tokens=self.cache_read_tokens,
                    cache_write_tokens=self.cache_write_tokens,
                ),
            )
        )


@dataclass(frozen=True)
class TextDelta:
    text: str = field(repr=False)


@dataclass(frozen=True)
class Completed:
    """Último evento do stream. `model` é o modelo que produziu a resposta final."""

    model: str
    usage: Usage
    stop_reason: StopReason


StreamEvent = TextDelta | Completed


@dataclass(frozen=True)
class GenerationResult:
    text: str = field(repr=False)
    completed: Completed


@dataclass(frozen=True)
class Capabilities:
    """Flags de capacidade (ADR-0006): o consumidor consulta-as, nunca assume."""

    streaming: bool
    exact_token_count: bool
    priced: bool
    tools: bool = False


class LLMGateway(Protocol):
    @property
    def provider(self) -> Provider: ...

    def capabilities(self) -> Capabilities: ...

    async def count_tokens(self, request: GenerationRequest) -> int: ...

    def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        """Deltas de texto e um `Completed` final.

        - O modelo do pedido tem de ser um dos configurados; senão, `ProviderError` antes da chamada.
        - `timeout_seconds` é um prazo total do stream, verificado a cada evento; o prazo do turno
          (desde a recepção da mensagem) é do consumidor (E3.4).
        - Os erros levam `after_first_delta`: depois do primeiro delta não se repete (AC-004-09).
        """
        ...

    async def aclose(self) -> None: ...


async def generate(
    gateway: LLMGateway, request: GenerationRequest, meter: UsageMeter | None = None
) -> GenerationResult:
    """Consome o stream e junta o texto: uma só implementação para todos os adaptadores."""
    parts: list[str] = []
    completed: Completed | None = None
    async for event in gateway.stream(request, meter):
        if isinstance(event, TextDelta):
            parts.append(event.text)
        else:
            completed = event
    if completed is None:
        # Um adaptador que termina sem `Completed` está partido; não inventamos usage.
        raise RuntimeError("stream terminou sem evento Completed")
    return GenerationResult(text="".join(parts), completed=completed)
