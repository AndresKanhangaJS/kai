# Changelog dos contratos

Formato: uma entrada por alteração, com a classificação de compatibilidade (`kai-contract`). Uma major nova é publicada em paralelo com a anterior durante pelo menos um milestone, com a data de fim de vida da anterior.

## v1, sem alteração de schema (2026-11-23, M03 E2.1)

**Classificação:** compatível (só a descrição do canal `commands` no AsyncAPI).

- O canal `kai.commands` descreve o retry no consumidor e a DLQ pelo broker (ADR-0018, que substitui o ADR-0003). Topologia real em `infra/rabbitmq/` ([`rabbitmq.md`](../../docs/engineering/rabbitmq.md)).

## v1 (2026-11-22, M02 E3)

**Classificação:** inicial (sem consumidores).

- OpenAPI `internal-v1`: `POST /internal/v1/tool-authorizations` (`allow` com grant, `deny`, `requires_approval`); `GET /health/live`; `GET /health/ready`.
- Envelope `envelope.v1` e tipos comuns `common.v1`.
- Mensagens:
  - `ai.conversation.turn.requested.v1`
  - `ai.conversation.turn.completed.v1`
  - `ai.conversation.turn.failed.v1`
  - `ai.mission.step.reported.v1`
  - `ai.mission.step.resume.v1`
  - `ai.mission.cancel.requested.v1`
  - `ai.model.usage.recorded.v1`
- Exemplos: 23 válidos e 69 inválidos, cada inválido com o erro esperado declarado.
- Revisão de segurança aplicada antes da publicação: sem `tainted` no `step.reported` (o taint é derivado pelo Laravel); grant e aprovação de uso único; `arguments`/`output` limitados; `tracestate` sem CR/LF; timestamps RFC 3339 por pattern.
- Spec: [SPEC-003](../../docs/specs/003-contratos-v1.md).
