# packages/contracts

Contratos entre o Core Platform (Laravel, `kai-api`) e o AI Engine (Python, `kai-ai-engine`). Spec: [SPEC-003](../../docs/specs/003-contratos-v1.md). Decisões: ADR-0002, ADR-0003, ADR-0010, ADR-0013.

| Ficheiro | O quê |
|---|---|
| [`openapi/internal-v1.yaml`](openapi/internal-v1.yaml) | REST interno (OpenAPI 3.1): `POST /internal/v1/tool-authorizations`, `/health/live`, `/health/ready` |
| [`asyncapi/kai-v1.yaml`](asyncapi/kai-v1.yaml) | RabbitMQ (AsyncAPI 3.0): `kai.commands` e `kai.events` |
| [`schemas/envelope.v1.json`](schemas/envelope.v1.json) | Envelope comum de todas as mensagens |
| [`schemas/common.v1.json`](schemas/common.v1.json) | Tipos partilhados (UUID, `user_id`, `tool_ref`, erro seguro, USD) |
| `schemas/<tipo>.v<major>.json` | Uma mensagem (envelope + payload) ou um corpo HTTP |
| `examples/<tipo>/{valid,invalid}/` | Exemplos sintéticos: os válidos têm de passar e os inválidos têm de falhar pelo erro declarado em `invalid/expected-errors.json` |
| [`tooling/`](tooling/) | Validador da CI (E2.3) e os meta-schemas oficiais |
| [`CHANGELOG.md`](CHANGELOG.md) | Histórico e classificação de compatibilidade |

## Mensagens v1

| Tipo | Direcção | Idempotência |
|---|---|---|
| `ai.conversation.turn.requested.v1` | Laravel → Python (comando) | `turn:{user_message_id}` |
| `ai.conversation.turn.completed.v1` | Python → Laravel (evento) | `turn_completed:{user_message_id}` |
| `ai.conversation.turn.failed.v1` | Python → Laravel (evento) | `turn_failed:{user_message_id}` |
| `ai.mission.step.reported.v1` | Python → Laravel (evento) | `step:{step_id}:{kind}` |
| `ai.mission.step.resume.v1` | Laravel → Python (comando) | `resume:{approval_id}` |
| `ai.mission.cancel.requested.v1` | Laravel → Python (comando) | `cancel:{mission_id}` |
| `ai.model.usage.recorded.v1` | Python → Laravel (evento) | `usage:{usage_id}` |

## Regras
- O execution grant **nunca** vai no RabbitMQ; só na resposta `allow` de `tool-authorizations` (SPEC-003 §2.2). Um grant por passo; a aprovação é consumida (§2.7).
- O taint da missão é derivado só pelo Laravel (§2.6); nenhum contrato o transporta.
- Nos eventos Python → Laravel, o dono e as ligações derivam-se do registo do Laravel; os IDs do payload só servem para lookup.
- O nível e o modo de uma ferramenta nunca vêm do Python; o Laravel deriva-os do Tool Registry.
- `additionalProperties: false` vale para o **produtor**: o que publica tem de validar. O consumidor das mensagens é *tolerant reader* e ignora campos opcionais que ainda não conhece (`contracts.md`). **Excepção:** `POST /internal/v1/tool-authorizations` rejeita com 422 qualquer campo fora do schema.
- Exemplos e fixtures só com dados sintéticos.
- Uma alteração ao contrato muda primeiro aqui, com exemplos e uma entrada no `CHANGELOG`, e pede a aprovação do owner.

## Validar

```bash
scripts/ci/contracts.sh
```

O validador corre numa imagem própria (`python:3.14-slim` fixada por digest; `jsonschema` e `PyYAML` com hashes), sem rede e com o pacote montado só para leitura. Verifica:
- os JSON Schemas (draft 2020-12);
- o OpenAPI contra o meta-schema oficial 3.1;
- o AsyncAPI contra o meta-schema oficial 3.0.0;
- todas as `$ref`;
- os exemplos;
- as regras do KAI: `user_id` obrigatório, nenhum campo de grant, token ou credencial e nenhum objecto aberto nas mensagens, seguindo os `$ref`;
- o próprio validador, com schemas maus que tem de detectar.

## Meta-schemas versionados (`tooling/meta/`)

| Ficheiro | Fonte | sha256 | Licença |
|---|---|---|---|
| `openapi-3.1-2022-10-07.json` | https://spec.openapis.org/oas/3.1/schema/2022-10-07 | `da01ba28852cac0de53893797cb8d1942bc3b05084f526dcc216717dec314ed0` | Apache-2.0 (OpenAPI Initiative) |
| `asyncapi-3.0.0.json` | `asyncapi/spec-json-schemas`, commit `eee8d2217d23b22c475090c0e12f20801f531f11`, `schemas/3.0.0.json` | `1786a007ac00344a8f529e5a6fc5db786b0be6757e0b94a8b95a8a6a52b7fe9a` | Apache-2.0 |

Obtidos e verificados a 2026-11-22. O `validate.py` confirma estes sha256 antes de os usar; um meta-schema alterado faz a CI falhar.
