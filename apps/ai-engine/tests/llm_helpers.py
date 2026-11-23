"""Ajudas comuns aos testes do LLM Gateway (sem rede)."""

import asyncio
import io
import json
import logging
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from kai_ai_engine.llm.gateway import ChatMessage, GenerationRequest, LLMGateway, StreamEvent
from kai_ai_engine.logging import JsonFormatter, configure_logging

FIXTURES = Path(__file__).parent / "fixtures"


def run[T](coro: Awaitable[T]) -> T:
    async def wrapper() -> T:
        return await coro

    return asyncio.run(wrapper())


def request(
    content: str = "Olá", *, model: str = "claude-opus-5-5", max_output_tokens: int = 256
) -> GenerationRequest:
    return GenerationRequest(
        model=model,
        messages=(ChatMessage(role="user", content=content),),
        max_output_tokens=max_output_tokens,
        timeout_seconds=30,
    )


def collect(gateway: LLMGateway, req: GenerationRequest) -> list[StreamEvent]:
    async def go() -> list[StreamEvent]:
        return [event async for event in gateway.stream(req)]

    return run(go())


def expect_raises(fn: Callable[[], object], exc_type: type[BaseException]) -> BaseException:
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError(f"{exc_type.__name__} não foi levantada")


@contextmanager
def captured_logs() -> Iterator[io.StringIO]:
    """Logs JSON do processo com a configuração de produção, mas em DEBUG (o pior caso)."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    configure_logging(logging.DEBUG)
    root.addHandler(handler)
    try:
        yield stream
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def log_entries(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
