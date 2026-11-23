"""Fornecedor `fake` (P-015, AC-10): determinístico, sem rede, com falhas injectáveis."""

import time

import pytest

from kai_ai_engine.llm.errors import ProviderUnavailableError
from kai_ai_engine.llm.fake import FAKE_MODEL, FakeConfigError, FakeGateway, FakeOptions, options_from_env
from kai_ai_engine.llm.gateway import Completed, TextDelta, generate

from .llm_helpers import collect, expect_raises, request, run


def test_e_deterministico_e_os_deltas_somam_a_resposta() -> None:
    req = request("uma frase com várias palavras para partir")
    first = collect(FakeGateway(), req)
    second = collect(FakeGateway(), req)
    assert first == second
    deltas = [e.text for e in first if isinstance(e, TextDelta)]
    assert len(deltas) > 1
    result = run(generate(FakeGateway(), req))
    assert "".join(deltas) == result.text == "Resposta fake: uma frase com várias palavras para partir"
    assert result.completed.stop_reason == "end_turn"
    assert result.completed.model == FAKE_MODEL


def test_o_ultimo_evento_e_completed_com_usage() -> None:
    events = collect(FakeGateway(), request("duas palavras"))
    last = events[-1]
    assert isinstance(last, Completed)
    assert last.usage.input_tokens == 2
    assert last.usage.output_tokens == 4
    assert all(isinstance(e, TextDelta) for e in events[:-1])


def test_respeita_max_output_tokens() -> None:
    result = run(generate(FakeGateway(), request("a b c d e f g h", max_output_tokens=3)))
    assert result.text == "Resposta fake: a"
    assert result.completed.stop_reason == "max_tokens"
    assert result.completed.usage.output_tokens == 3


def test_falha_transitoria_antes_do_primeiro_delta_n_vezes() -> None:
    gateway = FakeGateway(FakeOptions(fail_before_first_delta=2))
    for _ in range(2):
        exc = expect_raises(lambda: collect(gateway, request()), ProviderUnavailableError)
        assert isinstance(exc, ProviderUnavailableError) and exc.retryable
    assert isinstance(collect(gateway, request())[-1], Completed)
    assert gateway.calls == 3


def test_falha_depois_de_um_delta() -> None:
    gateway = FakeGateway(FakeOptions(fail_after_deltas=1, words_per_delta=1))
    received: list[str] = []

    async def go() -> None:
        async for event in gateway.stream(request("a b c")):
            if isinstance(event, TextDelta):
                received.append(event.text)

    with pytest.raises(ProviderUnavailableError):
        run(go())
    assert received == ["Resposta"]


def test_atraso_por_delta_e_resposta_fixa() -> None:
    gateway = FakeGateway(FakeOptions(delay_per_delta=0.02, words_per_delta=1, script="x y z"))
    started = time.monotonic()
    result = run(generate(gateway, request("ignorado")))
    assert result.text == "x y z"
    assert time.monotonic() - started >= 0.05


def test_count_tokens_deterministico() -> None:
    assert run(FakeGateway().count_tokens(request("um dois três"))) == 3


def test_opcoes_do_ambiente() -> None:
    opts = options_from_env(
        {
            "KAI_FAKE_DELAY_PER_DELTA": "0.5",
            "KAI_FAKE_FAIL_BEFORE_FIRST_DELTA": "2",
            "KAI_FAKE_FAIL_AFTER_DELTAS": "3",
        }
    )
    assert (opts.delay_per_delta, opts.fail_before_first_delta, opts.fail_after_deltas) == (0.5, 2, 3)
    assert options_from_env({}) == FakeOptions()


def test_negativo_opcao_invalida_nomeia_a_variavel_sem_o_valor() -> None:
    with pytest.raises(FakeConfigError, match="KAI_FAKE_DELAY_PER_DELTA") as info:
        options_from_env({"KAI_FAKE_DELAY_PER_DELTA": "valor-secreto"})
    assert "valor-secreto" not in str(info.value)
    with pytest.raises(FakeConfigError):
        options_from_env({"KAI_FAKE_FAIL_AFTER_DELTAS": "-1"})


def test_o_fake_nao_tem_preco_nem_ferramentas() -> None:
    caps = FakeGateway().capabilities()
    assert (caps.priced, caps.tools, caps.streaming) == (False, False, True)


@pytest.mark.parametrize("value", ["inf", "nan", "-1"])
def test_negativo_atraso_tem_de_ser_finito(value: str) -> None:
    with pytest.raises(FakeConfigError, match="KAI_FAKE_DELAY_PER_DELTA"):
        options_from_env({"KAI_FAKE_DELAY_PER_DELTA": value})


def test_o_meter_acompanha_o_stream_e_marca_falhas_depois_do_primeiro_delta() -> None:
    from kai_ai_engine.llm.gateway import UsageMeter

    meter = UsageMeter()
    gateway = FakeGateway(FakeOptions(fail_after_deltas=2, words_per_delta=1))
    exc = expect_raises(lambda: run(generate(gateway, request("a b c"), meter)), ProviderUnavailableError)
    assert isinstance(exc, ProviderUnavailableError) and exc.after_first_delta
    assert (meter.deltas, meter.output_tokens, meter.input_tokens) == (2, 2, 3)
