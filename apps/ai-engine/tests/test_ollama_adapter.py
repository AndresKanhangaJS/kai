"""Adaptador Ollama com NDJSON gravado e sintético, sem rede (SPEC-004 §8)."""

import json
from collections.abc import Callable

import httpx2
import pytest

from kai_ai_engine.llm.errors import LlmError, ProviderError, ProviderUnavailableError
from kai_ai_engine.llm.gateway import Completed, UsageMeter, generate
from kai_ai_engine.llm.ollama_adapter import OllamaConfigError, OllamaGateway, OllamaSettings

from .llm_helpers import FIXTURES, captured_logs, collect, expect_raises, request, run

CONTENT_CANARY = "canario-conteudo-ollama-0123456789"
MODEL = "llama-sintetico"
SETTINGS = OllamaSettings(host="http://ollama-sintetico:11434", model=MODEL)
Handler = Callable[[httpx2.Request], httpx2.Response]


def gateway(handler: Handler) -> OllamaGateway:
    return OllamaGateway(SETTINGS, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


def ok(_: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, content=(FIXTURES / "ollama" / "chat_ok.ndjson").read_bytes())


def test_stream_ndjson_com_usage() -> None:
    result = run(generate(gateway(ok), request(model=MODEL)))
    assert result.text == "Olá! Tudo bem."
    assert result.completed.stop_reason == "end_turn"
    assert (result.completed.usage.input_tokens, result.completed.usage.output_tokens) == (21, 5)


def test_o_pedido_leva_num_predict_e_o_system_primeiro() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return ok(req)

    req = request(model=MODEL, max_output_tokens=77)
    req = type(req)(**{**req.__dict__, "system": "és o KAI"})
    run(generate(gateway(handler), req))
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "http://ollama-sintetico:11434/api/chat"
    assert body["options"] == {"num_predict": 77}
    assert body["messages"][0] == {"role": "system", "content": "és o KAI"}
    assert "tools" not in body


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (lambda _: httpx2.Response(503, text=CONTENT_CANARY), ProviderUnavailableError),
        (lambda _: httpx2.Response(429), ProviderUnavailableError),
        (lambda _: httpx2.Response(404, text=CONTENT_CANARY), ProviderError),
        (
            lambda _: httpx2.Response(200, content=b'{"error":"' + CONTENT_CANARY.encode() + b'"}\n'),
            ProviderError,
        ),
        (lambda _: httpx2.Response(200, content=b"isto nao e json\n"), ProviderError),
        (
            lambda _: httpx2.Response(200, content=b'{"message":{"content":"a"},"done":false}\n'),
            ProviderUnavailableError,
        ),
    ],
)
def test_classificacao_de_erros(handler: Handler, expected: type[LlmError]) -> None:
    with captured_logs() as logs:
        exc = expect_raises(lambda: collect(gateway(handler), request(model=MODEL)), LlmError)
    assert type(exc) is expected
    assert CONTENT_CANARY not in str(exc) + repr(exc) + logs.getvalue()
    assert exc.__context__ is None and exc.__cause__ is None


def test_ligacao_e_timeout_sao_transitorios() -> None:
    for error in (httpx2.ConnectError("x"), httpx2.ReadTimeout("x")):

        def handler(_: httpx2.Request, error: Exception = error) -> httpx2.Response:
            raise error

        assert isinstance(
            expect_raises(lambda: collect(gateway(handler), request(model=MODEL)), LlmError),
            ProviderUnavailableError,
        )


@pytest.mark.parametrize(
    "host",
    [
        "file:///etc/passwd",
        "ftp://ollama:21",
        "ollama:11434",
        "http://user:pw@ollama:11434",
        "http://ollama?x=1",
        "http://ollama.exemplo.com:11434",
        "http://8.8.8.8:11434",
    ],
)
def test_negativo_ollama_host_invalido(host: str) -> None:
    with pytest.raises(OllamaConfigError) as info:
        OllamaSettings(host=host, model="m")
    assert host not in str(info.value)


def test_count_tokens_estimado_por_excesso_e_sem_preco() -> None:
    gw = gateway(ok)
    assert run(gw.count_tokens(request("a" * 30, model=MODEL))) >= 10
    caps = gw.capabilities()
    assert (caps.exact_token_count, caps.priced) == (False, False)
    assert isinstance(collect(gw, request(model=MODEL))[-1], Completed)


@pytest.mark.parametrize(
    "host",
    [
        "http://localhost:11434",
        "http://host.docker.internal:11434",
        "http://ollama:11434",
        "http://192.168.1.20:11434",
        "https://ollama.exemplo.com",
    ],
)
def test_hosts_aceites_http_so_na_rede_local(host: str) -> None:
    assert OllamaSettings(host=host, model="m").host == host


def test_negativo_redirect_nao_e_seguido() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(302, headers={"location": "http://atacante.exemplo/api/chat"})

    exc = expect_raises(lambda: collect(gateway(handler), request(model=MODEL)), LlmError)
    assert isinstance(exc, ProviderError)
    assert len(seen) == 1


def test_negativo_modelo_nao_configurado_nao_chama_o_fornecedor() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return ok(req)

    exc = expect_raises(lambda: collect(gateway(handler), request(model="outro-modelo")), LlmError)
    assert isinstance(exc, ProviderError) and exc.code == "model_not_allowed"
    assert seen == []


def test_erro_depois_do_primeiro_delta_fica_marcado_e_o_meter_tem_o_parcial() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        body = b'{"message":{"content":"a"},"done":false}\n{"error":"x"}\n'
        return httpx2.Response(200, content=body)

    meter = UsageMeter()

    async def go() -> None:
        async for _ in gateway(handler).stream(request(model=MODEL), meter):
            pass

    exc = expect_raises(lambda: run(go()), LlmError)
    assert isinstance(exc, LlmError) and exc.after_first_delta
    assert meter.deltas == 1
