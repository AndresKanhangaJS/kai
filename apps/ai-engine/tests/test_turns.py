"""Turno de conversa sem broker (SPEC-004 §3; AC-004-02, 04, 05, 06, 07 e 09).

Broker, inbox e publisher falsos; o tempo de backoff não corre (sleep injectado).
"""

import asyncio
import copy
import json
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from kai_ai_engine.contracts import ContractRegistry, contracts_dir
from kai_ai_engine.events import Event
from kai_ai_engine.inbox import ClaimState
from kai_ai_engine.llm.errors import ProviderUnavailableError, detached
from kai_ai_engine.llm.fake import FakeGateway, FakeOptions
from kai_ai_engine.llm.gateway import (
    Completed,
    GenerationRequest,
    ModelUsage,
    StreamEvent,
    TextDelta,
    Usage,
    UsageMeter,
)
from kai_ai_engine.publisher import PublishError
from kai_ai_engine.turns import Retry, TurnHandler

from .llm_helpers import captured_logs, log_entries, run

CONTRACTS = ContractRegistry()
EXAMPLES = contracts_dir() / "examples"
TURN = "ai.conversation.turn.requested.v1"
CANARY = "canario-conteudo-do-owner-nunca-nos-logs-42"


def example(message_type: str, name: str, kind: str = "valid") -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / message_type / kind / f"{name}.json").read_text())
    return data


def turn(**limits: Any) -> dict[str, Any]:
    body = copy.deepcopy(example(TURN, "minimo"))
    body["payload"]["limits"].update(limits)
    return body


class FakeDelivery:
    def __init__(
        self, body: bytes | dict[str, Any], *, user_id: str | None = "kai-api", routing_key: str | None = None
    ):
        if isinstance(body, dict):
            routing_key = routing_key or str(body.get("type"))
            body = json.dumps(body).encode()
        self.body = body
        self.user_id = user_id
        self.routing_key = routing_key
        self.acked = False
        self.rejected: bool | None = None  # requeue

    async def ack(self) -> None:
        assert not self.acked and self.rejected is None, "mensagem resolvida duas vezes"
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        assert not self.acked and self.rejected is None, "mensagem resolvida duas vezes"
        self.rejected = requeue

    async def nack(self, *, requeue: bool = True) -> None:
        assert not self.acked and self.rejected is None, "mensagem resolvida duas vezes"
        self.rejected = requeue

    @property
    def dead_lettered(self) -> bool:
        return self.rejected is False


class FakeInbox:
    def __init__(self, initial: dict[str, str] | None = None, *, claim_fails: int = 0, done_fails: int = 0):
        self.states: dict[str, str] = dict(initial or {})
        self.claim_fails = claim_fails
        self.done_fails = done_fails

    async def claim(self, message_id: str, ttl_seconds: int) -> ClaimState:
        assert ttl_seconds > 60
        if self.claim_fails:
            self.claim_fails -= 1
            raise ConnectionError("redis em baixo")
        state = self.states.get(message_id)
        if state is None:
            self.states[message_id] = "processing"
            return "new"
        return "done" if state == "done" else "processing"

    async def mark_done(self, message_id: str) -> None:
        if self.done_fails:
            self.done_fails -= 1
            raise ConnectionError("redis em baixo")
        self.states[message_id] = "done"

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


class FakePublisher:
    def __init__(self, *, fails: int = 0) -> None:
        self.events: list[Event] = []
        self.fails = fails

    async def publish(self, event: Event) -> None:
        if self.fails:
            self.fails -= 1
            raise PublishError("sem confirm")
        self.events.append(event)

    def of(self, suffix: str) -> list[dict[str, Any]]:
        return [e.body for e in self.events if e.type.endswith(suffix)]


class Harness:
    def __init__(
        self, gateway: Any = None, inbox: FakeInbox | None = None, publisher: FakePublisher | None = None
    ):
        self.gateway = gateway or FakeGateway()
        self.inbox = inbox or FakeInbox()
        self.publisher = publisher or FakePublisher()
        self.sleeps: list[float] = []

        async def sleep(seconds: float) -> None:
            self.sleeps.append(seconds)

        self.handler = TurnHandler(
            gateway=self.gateway,
            inbox=self.inbox,
            publisher=self.publisher,
            contracts=CONTRACTS,
            sleep=sleep,
            provider_retry=Retry(attempts=5, base_delay=0.5, max_delay=8.0),
        )

    def deliver(self, body: bytes | dict[str, Any], **kwargs: Any) -> FakeDelivery:
        delivery = FakeDelivery(body, **kwargs)
        run(self.handler.handle(delivery))
        return delivery

    def assert_events_valid(self) -> None:
        for event in self.publisher.events:
            assert CONTRACTS.violations(event.type, event.body) == [], event.type


# --- AC-004-02: caminho feliz ------------------------------------------------------------------


def test_ac_004_02_turno_valido_da_completed_e_usage_validos_e_so_depois_ack() -> None:
    h = Harness()
    command = turn()
    delivery = h.deliver(command)
    assert delivery.acked
    h.assert_events_valid()
    (usage,) = h.publisher.of("usage.recorded.v1")
    (completed,) = h.publisher.of("turn.completed.v1")
    assert [e.type for e in h.publisher.events][-1].endswith("turn.completed.v1")
    last = command["payload"]["messages"][-1]["content"]
    assert completed["payload"]["content"] == "Resposta fake: " + last
    assert completed["payload"]["finish_reason"] == "end_turn"
    for event in (usage, completed):
        assert event["causation_id"] == command["id"]
        assert event["correlation_id"] == command["correlation_id"]
        assert event["producer"] == "kai-ai-engine"
        # Mesmo trace, span novo.
        assert event["traceparent"].split("-")[1] == command["traceparent"].split("-")[1]
        assert event["traceparent"] != command["traceparent"]
    assert completed["idempotency_key"] == f"turn_completed:{command['payload']['user_message_id']}"
    assert usage["payload"]["provider"] == "fake" and usage["payload"]["cost_usd"] == "0"
    assert usage["payload"]["output_tokens"] > 0
    assert h.inbox.states[command["id"]] == "done"


def test_o_prompt_de_sistema_e_versionado_e_as_mensagens_entram_como_user() -> None:
    seen: list[GenerationRequest] = []

    class Spy(FakeGateway):
        async def count_tokens(self, request: GenerationRequest) -> int:
            seen.append(request)
            return await super().count_tokens(request)

    h = Harness(gateway=Spy())
    h.deliver(turn())
    assert seen  # o fake também conta tokens dentro do stream
    for req in seen:
        assert req.system is not None and req.system.startswith("És o KAI")
        assert [m.role for m in req.messages] == ["user"]
        assert req.model == "fake-echo-1"


def test_max_output_tokens_atingido_e_completed_truncado() -> None:
    body = turn(max_output_tokens=3)
    h = Harness()
    h.deliver(body)
    (completed,) = h.publisher.of("turn.completed.v1")
    assert completed["payload"]["finish_reason"] == "max_output_tokens"


# --- AC-004-04: validação antes de gastar ------------------------------------------------------


def invalid_examples() -> list[str]:
    directory = EXAMPLES / TURN / "invalid"
    return sorted(p.stem for p in directory.iterdir() if p.stem != "expected-errors")


@pytest.mark.parametrize("name", invalid_examples())
def test_ac_004_04_cada_exemplo_invalido_vai_para_a_dlq_sem_chamada(name: str) -> None:
    expected = json.loads((EXAMPLES / TURN / "invalid" / "expected-errors.json").read_text())[name]
    h = Harness()
    body = example(TURN, name, "invalid")
    with captured_logs() as logs:
        delivery = h.deliver(body, routing_key=TURN)
    assert delivery.dead_lettered
    assert h.gateway.calls == 0 and h.publisher.events == [] and h.inbox.states == {}
    (entry,) = [e for e in log_entries(logs) if e["event"] == "message_rejected"]
    assert entry["reason"] == "schema"
    wanted = f"{expected['path'].lstrip('/') or '/'}:{expected['keyword']}"
    assert wanted in entry["violations"]  # type: ignore[operator]


@pytest.mark.parametrize("user_id", [None, "kai-admin", "kai-ai-engine", "KAI-API"])
def test_ac_004_04_negativo_user_id_amqp_diferente_de_kai_api(user_id: str | None) -> None:
    h = Harness()
    delivery = h.deliver(turn(), user_id=user_id)
    assert delivery.dead_lettered and h.gateway.calls == 0 and h.publisher.events == []


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"{nao e json", "invalid_json"),
        (b'{"type": "ai.conversation.turn.requested.v1", "x": NaN}', "invalid_json"),
        (b"[1, 2]", "invalid_envelope"),
        (json.dumps({"type": "ai.conversation.turn.completed.v1"}).encode(), "unsupported_type"),
        (json.dumps({"type": "ai.desconhecido.v1"}).encode(), "unsupported_type"),
    ],
)
def test_ac_004_04_negativo_corpo_invalido(body: bytes, reason: str) -> None:
    h = Harness()
    with captured_logs() as logs:
        delivery = h.deliver(body, routing_key=TURN)
    assert delivery.dead_lettered and h.gateway.calls == 0
    assert [e["reason"] for e in log_entries(logs) if e["event"] == "message_rejected"] == [reason]


def test_ac_004_04_negativo_routing_key_diferente_do_tipo() -> None:
    h = Harness()
    assert h.deliver(turn(), routing_key="ai.mission.step.resume.v1").dead_lettered
    assert h.gateway.calls == 0


def test_negativo_ferramentas_ainda_nao_suportadas_nao_chegam_ao_modelo() -> None:
    h = Harness()
    delivery = h.deliver(example(TURN, "com-historico-e-ferramentas"))
    assert delivery.dead_lettered and h.gateway.calls == 0 and h.publisher.events == []


def test_cancel_valido_e_confirmado_sem_efeito_e_step_resume_vai_para_a_dlq() -> None:
    h = Harness()
    assert h.deliver(example("ai.mission.cancel.requested.v1", "owner")).acked
    assert h.deliver(example("ai.mission.step.resume.v1", "aprovado")).dead_lettered
    assert h.gateway.calls == 0 and h.publisher.events == []


# --- AC-004-05: inbox ----------------------------------------------------------------------------


def test_ac_004_05_duplicado_ja_processado_e_confirmado_sem_chamada_nem_eventos() -> None:
    h = Harness()
    command = turn()
    assert h.deliver(command).acked
    published, calls = len(h.publisher.events), h.gateway.calls
    assert h.deliver(command).acked
    assert (len(h.publisher.events), h.gateway.calls) == (published, calls)


def test_processamento_interrompido_e_retomado() -> None:
    command = turn()
    h = Harness(inbox=FakeInbox({command["id"]: "processing"}))
    with captured_logs() as logs:
        assert h.deliver(command).acked
    assert "inbox_takeover" in [e["event"] for e in log_entries(logs)]
    assert len(h.publisher.of("turn.completed.v1")) == 1


def test_duplicado_concorrente_no_mesmo_processo_espera_pelo_original() -> None:
    h = Harness(gateway=FakeGateway(FakeOptions(delay_per_delta=0.01)))
    command = turn()

    async def both() -> tuple[FakeDelivery, FakeDelivery]:
        first, second = FakeDelivery(command), FakeDelivery(command)
        await asyncio.gather(h.handler.handle(first), h.handler.handle(second))
        return first, second

    first, second = run(both())
    assert first.acked and second.acked
    assert h.gateway.calls == 1 and len(h.publisher.of("turn.completed.v1")) == 1


# --- AC-004-07: orçamento ------------------------------------------------------------------------


def test_ac_004_07_orcamento_excedido_falha_antes_da_chamada_sem_usage() -> None:
    gateway = FakeGateway(FakeOptions(usd_per_mtok=Decimal(1_000_000)))
    h = Harness(gateway=gateway)
    assert h.deliver(turn(max_cost_usd="0.25")).acked
    h.assert_events_valid()
    (failed,) = h.publisher.of("turn.failed.v1")
    assert failed["payload"]["reason"] == "budget_exceeded"
    assert failed["payload"]["error"]["retryable"] is False
    assert gateway.calls == 0 and h.publisher.of("usage.recorded.v1") == []


def test_orcamento_suficiente_gera_e_custa() -> None:
    h = Harness(gateway=FakeGateway(FakeOptions(usd_per_mtok=Decimal(1))))
    h.deliver(turn(max_cost_usd="1"))
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert Decimal(usage["payload"]["cost_usd"]) > 0


# --- AC-004-09: retry só antes do primeiro delta ------------------------------------------------


def test_ac_004_09_falhas_transitorias_antes_do_delta_repetem_com_backoff() -> None:
    gateway = FakeGateway(FakeOptions(fail_before_first_delta=2))
    h = Harness(gateway=gateway)
    assert h.deliver(turn()).acked
    assert gateway.calls == 3 and len(h.sleeps) == 2
    assert 0.25 <= h.sleeps[0] <= 0.5 and 0.5 <= h.sleeps[1] <= 1.0
    assert len(h.publisher.of("turn.completed.v1")) == 1
    # As tentativas falhadas não consumiram tokens: só o usage da que gerou.
    assert len(h.publisher.of("usage.recorded.v1")) == 1


def test_ac_004_09_fornecedor_sempre_em_baixo_da_provider_unavailable() -> None:
    gateway = FakeGateway(FakeOptions(fail_before_first_delta=100))
    h = Harness(gateway=gateway)
    h.deliver(turn())
    (failed,) = h.publisher.of("turn.failed.v1")
    assert failed["payload"]["reason"] == "provider_unavailable"
    assert failed["payload"]["error"]["retryable"] is True
    assert gateway.calls == 5


def test_ac_004_09_negativo_falha_depois_do_primeiro_delta_nao_repete() -> None:
    gateway = FakeGateway(FakeOptions(fail_after_deltas=1, words_per_delta=1))
    h = Harness(gateway=gateway)
    h.deliver(turn())
    h.assert_events_valid()
    assert gateway.calls == 1 and h.sleeps == []
    (failed,) = h.publisher.of("turn.failed.v1")
    assert failed["payload"]["reason"] == "provider_error"
    # O que já foi gerado é facturado (AC-004-06).
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert usage["payload"]["output_tokens"] == 1


def test_sem_retry_se_o_backoff_passar_o_prazo() -> None:
    gateway = FakeGateway(FakeOptions(fail_before_first_delta=100))
    h = Harness(gateway=gateway)
    h.handler._provider_retry = Retry(attempts=5, base_delay=10.0, max_delay=10.0)
    h.deliver(turn(timeout_seconds=5))
    assert gateway.calls == 1 and h.sleeps == []
    assert h.publisher.of("turn.failed.v1")[0]["payload"]["reason"] == "provider_unavailable"


# --- AC-004-06: timeout ---------------------------------------------------------------------------


def test_ac_004_06_timeout_interrompe_e_regista_o_consumo_parcial() -> None:
    options = FakeOptions(delay_per_delta=0.3, words_per_delta=1, script=" ".join(["palavra"] * 50))
    h = Harness(gateway=FakeGateway(options))
    assert h.deliver(turn(timeout_seconds=1)).acked
    h.assert_events_valid()
    (failed,) = h.publisher.of("turn.failed.v1")
    assert failed["payload"]["reason"] == "timeout"
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert 0 < usage["payload"]["output_tokens"] < 50
    assert h.publisher.of("turn.completed.v1") == []


# --- respostas que não se entregam ---------------------------------------------------------------


class Scripted(FakeGateway):
    def __init__(self, text: str, stop: Any) -> None:
        super().__init__()
        self._text, self._stop = text, stop

    async def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        if self._text:
            yield TextDelta(self._text)
        usage = Usage(by_model=(ModelUsage(model="fake-echo-1", input_tokens=3, output_tokens=2),))
        yield Completed(model="fake-echo-1", usage=usage, stop_reason=self._stop)


@pytest.mark.parametrize(
    ("text", "stop", "code"),
    [
        ("parcial", "refusal", "model_refusal"),
        ("algo", "other", "unexpected_stop"),
        ("   ", "end_turn", "empty_response"),
        ("x" * 100_001, "end_turn", "response_too_long"),
    ],
)
def test_resposta_recusada_vazia_ou_grande_demais_falha_com_usage(text: str, stop: str, code: str) -> None:
    h = Harness(gateway=Scripted(text, stop))
    h.deliver(turn())
    h.assert_events_valid()
    (failed,) = h.publisher.of("turn.failed.v1")
    assert (failed["payload"]["reason"], failed["payload"]["error"]["code"]) == ("provider_error", code)
    assert len(h.publisher.of("usage.recorded.v1")) == 1


# --- infraestrutura ---------------------------------------------------------------------------------


def test_negativo_sem_confirm_nunca_ha_ack_nem_mark_done() -> None:
    h = Harness(publisher=FakePublisher(fails=100))
    command = turn()
    delivery = h.deliver(command)
    assert delivery.dead_lettered and not delivery.acked
    assert h.inbox.states[command["id"]] == "processing"
    assert len(h.sleeps) == 2  # 3 tentativas


def test_uma_falha_de_publicacao_repete_e_confirma() -> None:
    h = Harness(publisher=FakePublisher(fails=1))
    assert h.deliver(turn()).acked
    assert len(h.publisher.of("turn.completed.v1")) == 1


def test_inbox_em_baixo_volta_a_fila_sem_chamada() -> None:
    # Nada foi gasto: requeue (o x-delivery-limit acaba na DLQ), nunca DLQ à primeira (revisão E3.4a).
    h = Harness(inbox=FakeInbox(claim_fails=100))
    delivery = h.deliver(turn())
    assert delivery.rejected is True and not delivery.acked and h.gateway.calls == 0


def test_falha_a_marcar_done_confirma_na_mesma_os_eventos_ja_sairam() -> None:
    h = Harness(inbox=FakeInbox(done_fails=100))
    assert h.deliver(turn()).acked
    assert len(h.publisher.of("turn.completed.v1")) == 1


def test_erro_interno_vira_turn_failed_internal_error() -> None:
    class Broken(FakeGateway):
        def estimate_max_cost(self, input_tokens: int, max_output_tokens: int) -> Decimal:
            raise ZeroDivisionError

    h = Harness(gateway=Broken())
    assert h.deliver(turn()).acked
    h.assert_events_valid()
    assert h.publisher.of("turn.failed.v1")[0]["payload"]["reason"] == "internal_error"


# --- revisão de segurança da E3.4a ----------------------------------------------------------------


class BilledThenUnavailable(FakeGateway):
    """O fornecedor factura input (e raciocínio) e falha antes de qualquer texto."""

    async def stream(
        self, request: GenerationRequest, meter: UsageMeter | None = None
    ) -> AsyncIterator[StreamEvent]:
        self._calls += 1
        assert meter is not None
        meter.model = "fake-echo-1"
        meter.input_tokens = 1000
        meter.output_tokens = 500
        error = ProviderUnavailableError("provider_unavailable", "falha injectada")
        raise detached(error, after_first_delta=False)
        yield TextDelta("")  # pragma: no cover


def test_negativo_retries_facturados_nao_passam_o_orcamento_do_turno() -> None:
    # Tecto do pior caso: (in + max_out) a 1 USD/MTok; o orçamento cabe em 2 tentativas, não em 5.
    gateway = BilledThenUnavailable(FakeOptions(usd_per_mtok=Decimal(1)))
    h = Harness(gateway=gateway)
    request = GenerationRequest(model="fake-echo-1", messages=(), max_output_tokens=1000, timeout_seconds=60)
    worst = gateway.estimate_max_cost(run(gateway.count_tokens(turn_request(request))), 1000)
    assert h.deliver(turn(max_output_tokens=1000, max_cost_usd=str(worst * 2 + worst / 2))).acked
    h.assert_events_valid()
    assert gateway.calls == 2
    assert len(h.publisher.of("usage.recorded.v1")) == 2
    assert h.publisher.of("turn.failed.v1")[0]["payload"]["reason"] == "provider_unavailable"


def turn_request(request: GenerationRequest) -> GenerationRequest:
    body = turn()
    from kai_ai_engine.llm.gateway import ChatMessage
    from kai_ai_engine.turns import load_system_prompt

    messages = tuple(ChatMessage(role=m["role"], content=m["content"]) for m in body["payload"]["messages"])
    return GenerationRequest(
        model=request.model,
        messages=messages,
        max_output_tokens=request.max_output_tokens,
        timeout_seconds=request.timeout_seconds,
        system=load_system_prompt(),
    )


def test_retries_sem_facturacao_nao_gastam_orcamento() -> None:
    # Falhas antes de o fornecedor responder (sem tokens) não contam para o tecto.
    gateway = FakeGateway(FakeOptions(fail_before_first_delta=2, usd_per_mtok=Decimal(1)))
    h = Harness(gateway=gateway)
    h.deliver(turn(max_cost_usd="1"))
    assert gateway.calls == 3 and len(h.publisher.of("turn.completed.v1")) == 1


def test_erro_interno_a_meio_publica_o_usage_ja_facturado() -> None:
    class Crashes(FakeGateway):
        async def stream(
            self, request: GenerationRequest, meter: UsageMeter | None = None
        ) -> AsyncIterator[StreamEvent]:
            assert meter is not None
            meter.model = "fake-echo-1"
            meter.input_tokens = 10
            meter.output_tokens = 3
            yield TextDelta("ola")
            raise ZeroDivisionError

    h = Harness(gateway=Crashes())
    assert h.deliver(turn()).acked
    h.assert_events_valid()
    assert h.publisher.of("turn.failed.v1")[0]["payload"]["reason"] == "internal_error"
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert usage["payload"]["output_tokens"] == 3


def test_modelo_fora_do_contrato_nao_perde_o_usage() -> None:
    class OddModel(FakeGateway):
        async def stream(
            self, request: GenerationRequest, meter: UsageMeter | None = None
        ) -> AsyncIterator[StreamEvent]:
            yield TextDelta("ola")
            usage = Usage(by_model=(ModelUsage(model="modelo estranho\n", input_tokens=3, output_tokens=2),))
            yield Completed(model="modelo estranho\n", usage=usage, stop_reason="end_turn")

    h = Harness(gateway=OddModel())
    assert h.deliver(turn()).acked
    h.assert_events_valid()
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert usage["payload"]["model"] == h.gateway.model


def test_shutdown_a_meio_publica_o_usage_parcial_antes_de_voltar_a_fila() -> None:
    options = FakeOptions(delay_per_delta=0.05, words_per_delta=1, script=" ".join(["palavra"] * 100))
    h = Harness(gateway=FakeGateway(options))
    delivery = FakeDelivery(turn())

    async def scenario() -> None:
        task = asyncio.create_task(h.handler.handle(delivery))
        await asyncio.sleep(0.3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    run(scenario())
    h.assert_events_valid()
    (usage,) = h.publisher.of("usage.recorded.v1")
    assert 0 < usage["payload"]["output_tokens"] < 100
    assert h.publisher.of("turn.completed.v1") == h.publisher.of("turn.failed.v1") == []
    # O nack é do consumidor; a mensagem não foi resolvida aqui.
    assert not delivery.acked and delivery.rejected is None


def test_negativo_id_com_newline_final_vai_para_a_dlq() -> None:
    body = turn()
    body["id"] = body["id"] + "\n"
    h = Harness()
    assert h.deliver(body).dead_lettered and h.gateway.calls == 0


def test_negativo_contratos_em_falta_falham_no_arranque(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="contratos em falta"):
        TurnHandler(
            gateway=FakeGateway(),
            inbox=FakeInbox(),
            publisher=FakePublisher(),
            contracts=ContractRegistry(tmp_path),
        )


# --- privacidade -------------------------------------------------------------------------------------


def test_negativo_conteudo_do_owner_e_da_resposta_nunca_nos_logs() -> None:
    body = turn()
    body["payload"]["messages"][-1]["content"] = CANARY
    invalid = copy.deepcopy(body)
    invalid["payload"]["messages"][-1]["role"] = "system"
    with captured_logs() as logs:
        Harness().deliver(body)
        Harness().deliver(invalid)
        Harness(gateway=FakeGateway(FakeOptions(fail_after_deltas=1, words_per_delta=1))).deliver(body)
    text = logs.getvalue()
    assert "turn_finished" in text and "message_rejected" in text
    assert CANARY not in text


def test_o_prompt_existe_no_pacote() -> None:
    prompt = (
        Path(__file__).resolve().parents[1] / "src" / "kai_ai_engine" / "prompts" / "conversation" / "v1.md"
    )
    assert prompt.read_text(encoding="utf-8").strip()
