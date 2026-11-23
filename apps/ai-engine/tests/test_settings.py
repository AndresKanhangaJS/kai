"""Configuração: segredos só do ambiente, sem valores por omissão (SPEC-004 §5)."""

import io
import json
import logging

import pytest

from kai_ai_engine.logging import JsonFormatter
from kai_ai_engine.settings import SettingsError, load_settings

CANARY = "it-canario-nao-deve-aparecer-0123456789"


def test_negativo_sem_password_falha_no_arranque_sem_valores_na_mensagem() -> None:
    with pytest.raises(SettingsError, match="KAI_RABBITMQ_AI_ENGINE_PASSWORD"):
        load_settings({"RABBITMQ_HOST": "rabbitmq"})


def test_negativo_porto_invalido() -> None:
    with pytest.raises(SettingsError, match="RABBITMQ_PORT"):
        load_settings({"KAI_RABBITMQ_AI_ENGINE_PASSWORD": CANARY, "RABBITMQ_PORT": "abc"})


def test_valores_por_omissao_da_topologia() -> None:
    s = load_settings({"KAI_RABBITMQ_AI_ENGINE_PASSWORD": CANARY}).rabbitmq
    assert (s.host, s.port, s.vhost, s.user) == ("rabbitmq", 5672, "/kai", "kai-ai-engine")


def test_negativo_a_password_nunca_aparece_no_repr() -> None:
    settings = load_settings({"KAI_RABBITMQ_AI_ENGINE_PASSWORD": CANARY})
    assert CANARY not in repr(settings)
    assert CANARY not in str(settings)


def test_negativo_logs_de_excepcao_levam_so_a_classe() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger("teste.canario")
    log.addHandler(handler)
    try:
        raise ConnectionError(f"amqp://kai-ai-engine:{CANARY}@rabbitmq/kai")
    except ConnectionError:
        log.warning("rabbitmq_connect_failed", exc_info=True)
    finally:
        log.removeHandler(handler)
    out = stream.getvalue()
    assert CANARY not in out
    entry = json.loads(out)
    assert entry["event"] == "rabbitmq_connect_failed"
    assert entry["error_class"] == "ConnectionError"
    assert entry["service"] == "kai-ai-engine"


def test_negativo_campos_extra_nao_sobrepoem_os_reservados() -> None:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "turn_started", None, None)
    record.fields = {"event": "forjado", "level": "debug", "service": "outro", "run_id": "r-1"}
    entry = json.loads(JsonFormatter().format(record))
    assert (entry["event"], entry["level"], entry["service"]) == ("turn_started", "info", "kai-ai-engine")
    assert entry["run_id"] == "r-1"
