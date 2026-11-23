"""Configuração a partir do ambiente (SPEC-004 §5: segredos só em variáveis de ambiente).

Sem valores por omissão para segredos: falta de password falha no arranque, com uma
mensagem que nomeia a variável mas nunca o valor.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


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
class Settings:
    rabbitmq: RabbitMqSettings


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

    return Settings(
        rabbitmq=RabbitMqSettings(
            host=source.get("RABBITMQ_HOST", "rabbitmq"),
            port=int(port_raw),
            vhost=source.get("RABBITMQ_VHOST", "/kai"),
            user=source.get("RABBITMQ_USER", "kai-ai-engine"),
            password=password,
        )
    )
