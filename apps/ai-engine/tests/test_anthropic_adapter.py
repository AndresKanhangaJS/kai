"""Adaptador Anthropic com respostas gravadas e sintéticas, sem rede (SPEC-004 §8, AC-004-03/09)."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable

import httpx2
import pytest

from kai_ai_engine.llm.anthropic_adapter import FALLBACK_BETA, AnthropicGateway, AnthropicSettings
from kai_ai_engine.llm.errors import LlmError, ProviderError, ProviderUnavailableError
from kai_ai_engine.llm.gateway import Completed, TextDelta, UsageMeter, generate

from .llm_helpers import FIXTURES, captured_logs, collect, expect_raises, log_entries, request, run

KEY_CANARY = "canario-chave-anthropic-nao-deve-aparecer-0123456789"
CONTENT_CANARY = "canario-conteudo-nao-deve-aparecer-9876543210"

Handler = Callable[[httpx2.Request], httpx2.Response]


def gateway(handler: Handler, **overrides: object) -> AnthropicGateway:
    settings = AnthropicSettings(api_key=KEY_CANARY, **overrides)  # type: ignore[arg-type]
    return AnthropicGateway(settings, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


def sse(name: str) -> Handler:
    body = (FIXTURES / "anthropic" / name).read_bytes()

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    return handler


def error(status: int, error_type: str) -> Handler:
    def handler(_: httpx2.Request) -> httpx2.Response:
        # O fornecedor pode ecoar conteúdo do pedido na mensagem de erro.
        payload = {"type": "error", "error": {"type": error_type, "message": f"eco: {CONTENT_CANARY}"}}
        return httpx2.Response(status, json=payload)

    return handler


def raising(exc: Exception) -> Handler:
    def handler(_: httpx2.Request) -> httpx2.Response:
        raise exc

    return handler


def test_stream_emite_so_texto_e_usage_com_cache() -> None:
    events = collect(gateway(sse("stream_ok.sse")), request())
    deltas = [e.text for e in events if isinstance(e, TextDelta)]
    assert deltas == ["Olá", ", mundo", " sintético."]
    assert "PENSAMENTO" not in "".join(deltas)
    last = events[-1]
    assert isinstance(last, Completed)
    assert (last.model, last.stop_reason) == ("claude-opus-5-5", "end_turn")
    (u,) = last.usage.by_model
    assert (u.model, u.input_tokens, u.output_tokens, u.cache_read_tokens, u.cache_write_tokens) == (
        "claude-opus-5-5",
        12,
        42,
        100,
        50,
    )


def test_o_pedido_leva_max_tokens_fallback_sem_tools_e_a_chave_so_no_cabecalho() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return sse("stream_ok.sse")(req)

    run(generate(gateway(handler), request(max_output_tokens=321)))
    (req,) = seen
    body = json.loads(req.content)
    assert req.url.host == "api.anthropic.com"
    assert body["max_tokens"] == 321
    assert body["stream"] is True
    assert "tools" not in body and "tool_choice" not in body and "thinking" not in body
    assert body["output_config"] == {"effort": "medium"}
    assert body["fallbacks"] == [{"model": "claude-opus-5"}]
    assert FALLBACK_BETA in req.headers["anthropic-beta"]
    # O SDK 2.x envia a chave no Authorization; só aí, nunca no corpo nem no URL.
    assert [k for k, v in req.headers.items() if KEY_CANARY in v] == ["authorization"]
    assert KEY_CANARY not in req.content.decode() and KEY_CANARY not in str(req.url)


def test_sem_fallbacks_nao_envia_o_beta() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return sse("stream_ok.sse")(req)

    run(generate(gateway(handler, fallback_models=()), request()))
    assert "fallbacks" not in json.loads(seen[0].content)
    assert FALLBACK_BETA not in seen[0].headers.get("anthropic-beta", "")


def test_fallback_usage_por_tentativa_e_modelo_final() -> None:
    result = run(generate(gateway(sse("stream_fallback.sse")), request()))
    assert result.text == "Resposta do fallback."
    assert result.completed.model == "claude-opus-5"
    assert [(u.model, u.output_tokens) for u in result.completed.usage.by_model] == [
        ("claude-opus-5-5", 0),
        ("claude-opus-5", 7),
    ]


def test_recusa_da_cadeia_inteira_vem_como_stop_reason_com_usage() -> None:
    result = run(generate(gateway(sse("stream_refusal.sse")), request()))
    assert result.completed.stop_reason == "refusal"
    assert result.completed.usage.output_tokens == 3


def test_count_tokens_e_exacto_pelo_endpoint() -> None:
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json={"input_tokens": 17})

    assert run(gateway(handler).count_tokens(request())) == 17
    assert seen[0].url.path == "/v1/messages/count_tokens"


@pytest.mark.parametrize(
    ("handler", "expected", "status"),
    [
        (error(429, "rate_limit_error"), ProviderUnavailableError, 429),
        (error(529, "overloaded_error"), ProviderUnavailableError, 529),
        (error(500, "api_error"), ProviderUnavailableError, 500),
        (error(503, "api_error"), ProviderUnavailableError, 503),
        # Um 5xx de tipo desconhecido classifica-se pelo status, não pelo tipo.
        (error(502, "tipo_desconhecido"), ProviderUnavailableError, 502),
        (lambda _: httpx2.Response(504, text="<html>gateway</html>"), ProviderUnavailableError, 504),
        (raising(httpx2.ConnectError("recusada")), ProviderUnavailableError, None),
        (raising(httpx2.ReadTimeout("lento")), ProviderUnavailableError, None),
        (error(400, "invalid_request_error"), ProviderError, 400),
        (error(401, "authentication_error"), ProviderError, 401),
        (error(403, "permission_error"), ProviderError, 403),
        (error(404, "not_found_error"), ProviderError, 404),
    ],
)
def test_classificacao_de_erros(handler: Handler, expected: type[LlmError], status: int | None) -> None:
    exc = expect_raises(lambda: collect(gateway(handler), request()), LlmError)
    assert type(exc) is expected
    assert isinstance(exc, LlmError)
    assert exc.status == status
    assert exc.retryable is (expected is ProviderUnavailableError)
    # Sem a excepção original encadeada: a mensagem do SDK não viaja no traceback.
    assert exc.__cause__ is None and exc.__context__ is None
    assert exc.after_first_delta is False


def test_count_tokens_classifica_erros_igual() -> None:
    exc = expect_raises(
        lambda: run(gateway(error(529, "overloaded_error")).count_tokens(request())), LlmError
    )
    assert isinstance(exc, ProviderUnavailableError)


def test_negativo_chave_e_conteudo_nunca_em_erros_repr_nem_logs() -> None:
    gw = gateway(error(400, "invalid_request_error"))
    with captured_logs() as logs:
        exc = expect_raises(lambda: collect(gw, request(CONTENT_CANARY)), ProviderError)
        run(generate(gateway(sse("stream_ok.sse")), request(CONTENT_CANARY)))
    rendered = " ".join([str(exc), repr(exc), repr(gw._settings), logs.getvalue()])
    assert KEY_CANARY not in rendered
    assert CONTENT_CANARY not in rendered
    events = [e["event"] for e in log_entries(logs)]
    assert "llm_provider_error" in events and "llm_stream_completed" in events


def test_capacidades() -> None:
    caps = gateway(sse("stream_ok.sse")).capabilities()
    assert (caps.priced, caps.exact_token_count, caps.tools) == (True, True, False)
    assert gateway(sse("stream_ok.sse")).possible_models == ("claude-opus-5-5", "claude-opus-5")


def test_erro_a_meio_do_stream_classifica_pelo_tipo() -> None:
    """Um evento `error` no SSE chega com HTTP 200: só o tipo diz se é transitório."""
    head = (FIXTURES / "anthropic" / "stream_ok.sse").read_text().split("event: content_block_stop")[0]
    for error_type, expected in (
        ("overloaded_error", ProviderUnavailableError),
        ("invalid_request_error", ProviderError),
    ):
        payload = {"type": "error", "error": {"type": error_type, "message": CONTENT_CANARY}}
        body = head + f"event: error\ndata: {json.dumps(payload)}\n\n"

        def handler(_: httpx2.Request, body: str = body) -> httpx2.Response:
            return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())

        async def go(handler: Handler = handler) -> None:
            async for _ in gateway(handler).stream(request()):
                pass

        exc = expect_raises(lambda: run(go()), LlmError)
        assert type(exc) is expected, error_type
        assert CONTENT_CANARY not in str(exc) + repr(exc)


OK_SSE = (FIXTURES / "anthropic" / "stream_ok.sse").read_text()


def streaming(chunks: list[str], *, fail: Exception | None = None, pause: float = 0.0) -> Handler:
    """Corpo SSE servido aos bocados (e opcionalmente cortado a meio por uma excepção)."""

    async def body() -> AsyncIterator[bytes]:
        for chunk in chunks:
            if pause:
                await asyncio.sleep(pause)
            yield chunk.encode()
        if fail is not None:
            raise fail

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body())

    return handler


def events_until(marker: str) -> list[str]:
    """Eventos SSE completos antes do evento que contém `marker`."""
    head = OK_SSE[: OK_SSE.index(marker)]
    head = head[: head.rindex("\n\n")]
    return [e + "\n\n" for e in head.split("\n\n") if e.strip()]


def consume(gw: AnthropicGateway, meter: UsageMeter, **kwargs: object) -> None:
    async def go() -> None:
        async for _ in gw.stream(request(**kwargs), meter):  # type: ignore[arg-type]
            pass

    run(go())


@pytest.mark.parametrize(
    ("fail", "expected"),
    [
        (httpx2.RemoteProtocolError("peer closed"), ProviderUnavailableError),
        (httpx2.ReadTimeout("lento"), ProviderUnavailableError),
    ],
)
def test_ligacao_cortada_a_meio_e_classificada_e_o_meter_guarda_o_parcial(
    fail: Exception, expected: type[LlmError]
) -> None:
    """Achado 1 e 4 da revisão: o uso consumido não se perde e o erro do transporte é mapeado."""
    chunks = events_until('"text": ", mundo"')
    meter = UsageMeter()
    exc = expect_raises(lambda: consume(gateway(streaming(chunks, fail=fail)), meter), LlmError)
    assert type(exc) is expected
    assert isinstance(exc, LlmError) and exc.after_first_delta is True
    assert exc.__context__ is None and exc.__cause__ is None
    partial = meter.snapshot()
    assert (partial.input_tokens, partial.cache_read_tokens, partial.cache_write_tokens) == (12, 100, 50)
    assert partial.by_model[0].model == "claude-opus-5-5"
    assert meter.deltas == 1


def test_prazo_total_mesmo_com_um_fornecedor_que_pinga_devagar() -> None:
    """Achado 5: o timeout é um prazo total, não só por leitura."""
    chunks = [e + "\n\n" for e in OK_SSE.split("\n\n") if e.strip()]
    meter = UsageMeter()
    exc = expect_raises(
        lambda: run(
            generate(
                gateway(streaming(chunks, pause=0.05)),
                type(request())(**{**request().__dict__, "timeout_seconds": 0.12}),
                meter,
            )
        ),
        LlmError,
    )
    assert isinstance(exc, ProviderUnavailableError) and exc.code == "provider_timeout"
    assert meter.input_tokens == 12


def test_negativo_modelo_nao_configurado_nao_chama_o_fornecedor() -> None:
    """Achado 6: o modelo vem da configuração; outro é recusado antes da chamada."""
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return sse("stream_ok.sse")(req)

    gw = gateway(handler)
    for call in (
        lambda: collect(gw, request(model="claude-sonnet-5-5")),
        lambda: run(gw.count_tokens(request(model="claude-fable-5-2"))),
    ):
        exc = expect_raises(call, LlmError)
        assert isinstance(exc, ProviderError) and exc.code == "model_not_allowed"
    assert seen == []


def test_negativo_credenciais_e_url_do_ambiente_sao_ignorados(monkeypatch: pytest.MonkeyPatch) -> None:
    """O SDK não troca a chave explícita por tokens, perfis ou base_url do ambiente."""
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "token-do-ambiente-canario")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-do-ambiente-canario")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://atacante.exemplo")
    monkeypatch.setenv("ANTHROPIC_PROFILE", "perfil-canario")
    seen: list[httpx2.Request] = []

    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return sse("stream_ok.sse")(req)

    run(generate(gateway(handler), request()))
    (req,) = seen
    assert req.url.host == "api.anthropic.com"
    headers = " ".join(f"{k}={v}" for k, v in req.headers.items())
    assert "canario" not in headers.replace(KEY_CANARY, "")
    assert [k for k, v in req.headers.items() if KEY_CANARY in v] == ["authorization"]


def test_modificadores_de_preco_sao_assinalados() -> None:
    """Achado 9: geografia fora da global, fast mode e cache de 1 h não estão na tabela."""
    body = OK_SSE.replace(
        '"cache_creation_input_tokens": 50}',
        '"cache_creation_input_tokens": 50, "inference_geo": "us", "speed": "fast", '
        '"cache_creation": {"ephemeral_1h_input_tokens": 50, "ephemeral_5m_input_tokens": 0}}',
    )
    result = run(generate(gateway(streaming([body])), request()))
    assert result.completed.usage.modifiers == {"inference_geo", "fast_mode", "cache_1h"}
    assert run(generate(gateway(sse("stream_ok.sse")), request())).completed.usage.modifiers == frozenset()


def test_iteracao_sem_modelo_usa_o_modelo_pedido_na_tentativa_principal() -> None:
    """Achado 8: a tentativa recusada nunca é cobrada ao preço do fallback."""
    body = (FIXTURES / "anthropic" / "stream_fallback.sse").read_text()
    body = body.replace('{"type": "message", "model": "claude-opus-5-5", ', '{"type": "message", ')
    result = run(generate(gateway(streaming([body])), request()))
    assert [u.model for u in result.completed.usage.by_model] == ["claude-opus-5-5", "claude-opus-5"]


def test_sse_malformado_a_meio_e_erro_permanente_sem_contexto() -> None:
    chunks = [*events_until('"text": ", mundo"'), 'event: content_block_delta\ndata: {"type": ' + "\n\n"]
    exc = expect_raises(lambda: consume(gateway(streaming(chunks)), UsageMeter()), LlmError)
    assert type(exc) is ProviderError
    assert isinstance(exc, LlmError) and exc.after_first_delta and exc.__context__ is None
