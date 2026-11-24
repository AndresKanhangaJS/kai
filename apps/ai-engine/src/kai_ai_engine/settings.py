"""Configuração a partir do ambiente (SPEC-004 §5: segredos só em variáveis de ambiente).

Sem valores por omissão para segredos: falta de password falha no arranque, com uma
mensagem que nomeia a variável mas nunca o valor.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, cast, get_args

from kai_ai_engine.inbox import RedisSettings
from kai_ai_engine.llm.anthropic_adapter import AnthropicSettings, Effort
from kai_ai_engine.llm.errors import PricingError
from kai_ai_engine.llm.fake import FakeConfigError, FakeOptions, options_from_env
from kai_ai_engine.llm.ollama_adapter import OllamaConfigError, OllamaSettings
from kai_ai_engine.llm.pricing import load_price_table

ModelProvider = Literal["fake", "anthropic", "ollama"]
# Fallback de recusa por omissão (servidor); todos com preço na tabela.
DEFAULT_FALLBACKS: dict[str, tuple[str, ...]] = {"claude-opus-5-5": ("claude-opus-5",)}


class SettingsError(RuntimeError):
    """Configuração em falta ou inválida; a mensagem nunca contém valores."""


@dataclass(frozen=True)
class RabbitMqSettings:
    host: str
    port: int
    vhost: str
    user: str
    # repr=False: a password nunca aparece em logs, tracebacks nem no repr.
    password: str = field(repr=False)


@dataclass(frozen=True)
class LlmSettings:
    """Fornecedor e modelo vêm só da configuração do serviço, nunca da mensagem (SPEC-004 §3)."""

    provider: ModelProvider
    fake: FakeOptions = field(default_factory=FakeOptions)
    anthropic: AnthropicSettings | None = None
    ollama: OllamaSettings | None = None


@dataclass(frozen=True)
class Settings:
    rabbitmq: RabbitMqSettings
    llm: LlmSettings
    redis: RedisSettings


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if env is None else env

    password = source.get("KAI_RABBITMQ_AI_ENGINE_PASSWORD", "")
    if not password:
        raise SettingsError(
            "falta a variável KAI_RABBITMQ_AI_ENGINE_PASSWORD (gera com scripts/dev/passwords.sh)"
        )

    port_raw = source.get("RABBITMQ_PORT", "5672")
    if not port_raw.isdigit() or not 0 < int(port_raw) < 65536:
        raise SettingsError("RABBITMQ_PORT tem de ser um porto TCP válido")

    redis_password = source.get("KAI_AI_ENGINE_REDIS_PASSWORD", "")
    if not redis_password:
        raise SettingsError(
            "falta a variável KAI_AI_ENGINE_REDIS_PASSWORD (gera com scripts/dev/passwords.sh)"
        )
    redis_port = source.get("AI_ENGINE_REDIS_PORT", "6379")
    if not redis_port.isdigit() or not 0 < int(redis_port) < 65536:
        raise SettingsError("AI_ENGINE_REDIS_PORT tem de ser um porto TCP válido")

    return Settings(
        llm=load_llm_settings(source),
        redis=RedisSettings(
            host=source.get("AI_ENGINE_REDIS_HOST", "ai-engine-redis"),
            port=int(redis_port),
            user="kai-ai-engine",
            password=redis_password,
        ),
        rabbitmq=RabbitMqSettings(
            host=source.get("RABBITMQ_HOST", "rabbitmq"),
            port=int(port_raw),
            vhost=source.get("RABBITMQ_VHOST", "/kai"),
            user=source.get("RABBITMQ_USER", "kai-ai-engine"),
            password=password,
        ),
    )


def load_llm_settings(source: Mapping[str, str]) -> LlmSettings:
    """Falha no arranque (AC-004-03), nunca em runtime; as mensagens não levam valores."""
    provider = source.get("MODEL_PROVIDER", "fake") or "fake"
    if provider not in get_args(ModelProvider):
        raise SettingsError("MODEL_PROVIDER tem de ser fake, anthropic ou ollama")

    if provider == "fake":
        try:
            return LlmSettings(provider="fake", fake=options_from_env(source))
        except FakeConfigError as exc:
            raise SettingsError(str(exc)) from None

    if provider == "ollama":
        host = source.get("OLLAMA_HOST", "")
        model = source.get("OLLAMA_MODEL", "")
        if not host or not model:
            raise SettingsError("MODEL_PROVIDER=ollama exige OLLAMA_HOST e OLLAMA_MODEL")
        try:
            return LlmSettings(provider="ollama", ollama=OllamaSettings(host=host, model=model))
        except OllamaConfigError as exc:
            raise SettingsError(str(exc)) from None

    api_key = source.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise SettingsError("MODEL_PROVIDER=anthropic exige ANTHROPIC_API_KEY")
    model = source.get("ANTHROPIC_MODEL", "") or "claude-opus-5-5"
    effort = source.get("ANTHROPIC_EFFORT", "") or "medium"
    if effort not in get_args(Effort):
        raise SettingsError("ANTHROPIC_EFFORT tem de ser low, medium, high, xhigh ou max")
    # Vazio: a omissão por modelo; "none": sem fallback; senão, lista separada por vírgulas.
    raw_fallbacks = source.get("ANTHROPIC_FALLBACK_MODELS", "").strip()
    if not raw_fallbacks:
        fallbacks = DEFAULT_FALLBACKS.get(model, ())
    elif raw_fallbacks == "none":
        fallbacks = ()
    else:
        fallbacks = tuple(m.strip() for m in raw_fallbacks.split(",") if m.strip())
    # Todos os modelos possíveis têm de ter preço: sem preço não há orçamento (AC-004-07).
    table = load_price_table()
    try:
        for m in (model, *fallbacks):
            table.price(m)
    except PricingError:
        raise SettingsError(
            f"ANTHROPIC_MODEL e ANTHROPIC_FALLBACK_MODELS têm de estar na tabela de preços {table.version}"
        ) from None
    return LlmSettings(
        provider="anthropic",
        anthropic=AnthropicSettings(
            api_key=api_key, model=model, effort=cast(Effort, effort), fallback_models=fallbacks
        ),
    )
