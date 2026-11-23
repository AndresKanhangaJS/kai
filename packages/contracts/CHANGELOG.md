# Changelog dos contratos

Formato: uma entrada por alteração, com a classificação de compatibilidade (`kai-contract`). Uma major nova é publicada em paralelo com a anterior durante pelo menos um milestone, com a data de fim de vida da anterior.

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
