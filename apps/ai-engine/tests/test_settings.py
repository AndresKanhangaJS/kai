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


# --- LLM (E3.3, AC-004-03): o fornecedor vem só da configuração e falha no arranque ---

BASE = {"KAI_RABBITMQ_AI_ENGINE_PASSWORD": CANARY}


def test_por_omissao_o_fornecedor_e_o_fake() -> None:
    assert load_settings(BASE).llm.provider == "fake"
    assert load_settings({**BASE, "MODEL_PROVIDER": ""}).llm.provider == "fake"


def test_negativo_fornecedor_desconhecido_e_recusado() -> None:
    with pytest.raises(SettingsError, match="MODEL_PROVIDER"):
        load_settings({**BASE, "MODEL_PROVIDER": "openai"})


def test_negativo_anthropic_sem_chave_falha_no_arranque() -> None:
    with pytest.raises(SettingsError, match="ANTHROPIC_API_KEY"):
        load_settings({**BASE, "MODEL_PROVIDER": "anthropic"})


def test_anthropic_com_chave_usa_opus_5_5_com_fallback_e_a_chave_nao_aparece() -> None:
    key = "canario-chave-settings-0123456789"
    settings = load_settings({**BASE, "MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": key})
    llm = settings.llm.anthropic
    assert llm is not None
    assert (llm.model, llm.effort, llm.fallback_models) == ("claude-opus-5-5", "medium", ("claude-opus-5",))
    assert key not in repr(settings) and key not in str(settings)


def test_fallbacks_configuraveis_e_desligaveis() -> None:
    env = {**BASE, "MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k"}
    llm = load_settings({**env, "ANTHROPIC_FALLBACK_MODELS": "none"}).llm.anthropic
    assert llm is not None and llm.fallback_models == ()
    # Vazio (o Compose passa sempre a variável) é a omissão, não "sem fallback".
    empty = load_settings({**env, "ANTHROPIC_FALLBACK_MODELS": ""}).llm.anthropic
    assert empty is not None and empty.fallback_models == ("claude-opus-5",)
    sonnet = load_settings({**env, "ANTHROPIC_MODEL": "claude-sonnet-5-5"}).llm.anthropic
    assert sonnet is not None and sonnet.fallback_models == ()


@pytest.mark.parametrize(
    "extra",
    [{"ANTHROPIC_MODEL": "claude-sem-preco"}, {"ANTHROPIC_FALLBACK_MODELS": "claude-sem-preco"}],
)
def test_negativo_modelo_sem_preco_falha_no_arranque(extra: dict[str, str]) -> None:
    with pytest.raises(SettingsError, match="tabela de preços"):
        load_settings({**BASE, "MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k", **extra})


def test_negativo_esforco_invalido() -> None:
    with pytest.raises(SettingsError, match="ANTHROPIC_EFFORT"):
        load_settings(
            {**BASE, "MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k", "ANTHROPIC_EFFORT": "turbo"}
        )


def test_negativo_ollama_exige_host_e_modelo_validos() -> None:
    with pytest.raises(SettingsError, match="OLLAMA_HOST e OLLAMA_MODEL"):
        load_settings({**BASE, "MODEL_PROVIDER": "ollama", "OLLAMA_HOST": "http://ollama:11434"})
    with pytest.raises(SettingsError, match="http"):
        load_settings({**BASE, "MODEL_PROVIDER": "ollama", "OLLAMA_HOST": "file:///x", "OLLAMA_MODEL": "m"})
    ok = load_settings(
        {**BASE, "MODEL_PROVIDER": "ollama", "OLLAMA_HOST": "http://ollama:11434", "OLLAMA_MODEL": "m"}
    )
    assert ok.llm.ollama is not None


def test_negativo_opcao_fake_invalida_falha_no_arranque() -> None:
    with pytest.raises(SettingsError, match="KAI_FAKE_DELAY_PER_DELTA"):
        load_settings({**BASE, "KAI_FAKE_DELAY_PER_DELTA": "x"})


def test_factory_escolhe_o_adaptador_e_nunca_cai_no_fake_em_silencio() -> None:
    from kai_ai_engine.llm.anthropic_adapter import AnthropicGateway
    from kai_ai_engine.llm.factory import build_gateway
    from kai_ai_engine.llm.fake import FakeGateway
    from kai_ai_engine.settings import LlmSettings

    assert isinstance(build_gateway(load_settings(BASE).llm), FakeGateway)
    anth = load_settings({**BASE, "MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "k"}).llm
    assert isinstance(build_gateway(anth), AnthropicGateway)
    with pytest.raises(ValueError, match="incompleta"):
        build_gateway(LlmSettings(provider="anthropic"))
