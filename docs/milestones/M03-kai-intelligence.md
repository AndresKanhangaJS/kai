# M03: KAI Intelligence

**Objectivo:** o owner conversa com o KAI no Command Center. A resposta chega em streaming e persiste, vinda de um AI Engine Python separado que fala com o Laravel só pelos contratos v1 (RabbitMQ e API interna). Cada pedido tem limites de custo e tempo, pode ser cancelado e deixa um trace único de ponta a ponta.

**Critério de aceitação (`analysis.md` §7):**
- AC-03, AC-09 e AC-10 (`docs/specs/001-mvp-fatia-vertical.md`);
- trace ponta a ponta React → Laravel → RabbitMQ → Python → LLM.

**Dependências:**
- M02: falta a CI verde no PR e o secret scanning activo (`docs/STATUS.md`).
- Contratos v1: [SPEC-003](../specs/003-contratos-v1.md).

**P-xxx deste milestone:**
- **P-002** (valores dos limites): recomendação aceite como ponto de partida, $1 por missão e $5 por dia. Os valores finais são medidos na E6.
- **P-018 (nova):** um turno de conversa é uma missão de um passo no M03?
  - Recomendação: sim. A AC-09 fala de missões e o `ai.mission.cancel.requested.v1` precisa de um `mission_id`.
  - O M05 generaliza para vários passos e ferramentas.
  - **Decide-se na spec da E4** (E4.1).
- **P-019:** bibliotecas AMQP e OpenTelemetry. **Fechada (2026-11-23)** pelos ADR-0016 e ADR-0017.

## Épico E1: spikes e decisões que desbloqueiam o resto (ADR-0009, P-019)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E1.1 | ~~Spike do Reverb~~ | spike | **Feito (2026-11-23).** `spikes/m03-reverb/run.sh`: Python só com a biblioteca padrão publica por HTTP (Pusher), e um cliente WebSocket recebe no canal privado: 100/100 por ordem, p95 8,9 ms; 500/500, p95 8,1 ms. Negativos recusados (assinatura errada → 401; auth inválida e origem não permitida → 4009). `laravel/reverb` v1.13.0 (MIT) e a extensão `pcntl` | — | Sim |
| E1.2 | Escolhe as bibliotecas AMQP (PHP e Python) | decisão (P-019) | **Feito (2026-11-23):** [ADR-0016](../adr/0016-clientes-amqp-php-e-python.md): `php-amqplib` 3.7.5 (LGPL aceite pelo owner) e `aio-pika` 10.2.3; o `bunny` fica excluído por conflito com a `react/promise` v3 | — | Sim |
| E1.3 | Escolhe o SDK OpenTelemetry (PHP e Python) e fixa a versão das semconv | decisão (P-019) | **Feito (2026-11-23):** [ADR-0017](../adr/0017-sdks-opentelemetry-e-semconv.md): instrumentação manual, SDK PHP 1.16.1, SDK Python 1.45.2, semconv 1.44.0 | — | Sim |
| E1.4 | ~~Regista o resultado do spike~~ | docs/ADR | **Feito (2026-11-23).** [ADR-0015](../adr/0015-streaming-de-tokens-reverb-confirmado.md) aceite a 2026-11-23; substitui o ADR-0009 | E1.1 | Não |

## Épico E2: infraestrutura de mensagens e observabilidade (ADR-0018, NFR-002)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E2.1 | ~~RabbitMQ 4.4 no Compose com definições versionadas~~ | infra | **Feito (2026-11-23).** `infra/rabbitmq/` ([`rabbitmq.md`](../engineering/rabbitmq.md)), profile `messaging`: vhost `/kai`, quorum queues limitadas, DLQ pelo broker, retry no consumidor ([ADR-0018](../adr/0018-mensageria-rabbitmq-outbox-retry-no-consumidor.md), substitui o ADR-0003, porque o retry pelo broker perdia mensagens), um utilizador por serviço sem `configure` nem acesso à DLQ, topic permissions por tipo, validação do `user_id`, 16 MiB; só o AMQP é alcançável; recusa arrancar sem passwords fortes. `scripts/ci/integration.sh` (job `integration`): 32 testes e 4 recusas de arranque; três defeitos injectados apanhados. `php-amqplib` 3.7.5, `phpseclib` 3.0.58 (a 4.x fica em `conflict`), `ext-sockets`; `composer audit` no `api.sh`. Duas revisões de segurança | E1.2 | Sim |
| E2.2 | ~~Acrescenta o `grafana/otel-lgtm` ao Compose, fixado por digest, só em `127.0.0.1`~~ | infra | **Feito (2026-11-23).** `grafana/otel-lgtm:0.40.0` por digest, profile `observability` ([`observability.md`](../engineering/observability.md)): `infra/otel-lgtm/start.sh` desliga o Grafana anónimo (Admin por omissão na imagem), o preinstall de plugins da internet e as estatísticas, e exige uma password de admin forte; só o Grafana é publicado, em `127.0.0.1:3000`; sem volume. Um span OTLP/HTTP sintético aparece no Tempo (`OtelLgtmTest`, no `integration.sh`); estatísticas de uso desligadas no Grafana, no Loki, no Tempo e no Pyroscope; password só em ficheiro 0400 (`$__file{}`); rede própria `telemetry`; quatro defeitos injectados apanhados; revisão de segurança aplicada. `scripts/dev/passwords.sh` substitui o `rabbitmq-passwords.sh` | E1.3 | Sim |
| E2.3 | Serviço Reverb no Compose | infra | **Parcial (2026-11-23):** o serviço `reverb` já existe (só em `127.0.0.1:8080`, origens restritas, healthy). Falta a autorização do canal privado (só o dono do `run`), na E4.6 | E1.4 | Não |

## Épico E3: AI Engine mínimo (`apps/ai-engine`) (ADR-0001, ADR-0006, ADR-0010)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E3.1 | Spec do AI Engine M03 (`kai-spec`): consumidor de `turn.requested`, LLM Gateway, publicação de eventos, health | spec | **Feito (2026-11-23):** [SPEC-004](../specs/004-ai-engine-m03.md) aprovada, 11 critérios; P-018 e P-020 fechadas; P-021 (dependências) aprovadas em lista na E3.2/E3.3 | — | Sim |
| E3.2 | ~~Cria `apps/ai-engine` (Python 3.14, FastAPI, imagem fixada por digest, deps com hashes) com `/health/live` e `/health/ready` conforme o contrato; sem porta publicada no host (ADR-0010)~~ | código | **Feito (2026-11-23).** [`apps/ai-engine`](../../apps/ai-engine/README.md): health conforme o `health.v1` (validado com `jsonschema`); readiness segue o estado real da ligação robusta ao RabbitMQ (ligação inicial em background com backoff e jitter); `scripts/ci/ai-engine.sh` sem rede (ruff, mypy strict, pytest: 14 testes) e job `ai-engine` na CI (ADR-0014: 7 jobs); serviço `ai-engine` no Compose (profile `messaging`, sem portas, `read_only`, `cap_drop: ALL`); `integration.sh`: health real, sem portas publicadas, 503 com o RabbitMQ parado e 200 depois da reconexão (bug real apanhado aqui); revisão de segurança aplicada: rede própria `messaging` (o ai-engine não chega ao MySQL nem ao Redis, testado), locks com o `uv` oficial por digest e `--no-build`, só wheels, sem pip no runtime, limites de memória e processos, password nunca nos logs (testado). Três defeitos injectados apanhados | E3.1 | Não |
| E3.3 | Porta `LLMGateway` (`generate`, `stream`, `count_tokens`) com os adaptadores `fake` (determinístico, por omissão), Anthropic e Ollama | código | Os testes correm só com o `fake`, sem rede (AC-10); os adaptadores reais estão atrás de flags de capacidade; as chaves vêm de variáveis de ambiente e nunca aparecem em logs | E3.2 | Não |
| E3.4 | Consumidor de `turn.requested.v1` com inbox (dedupe por `id`), validação contra o schema, streaming de deltas (E2.3), `turn.completed`/`turn.failed` e `usage.recorded` | código | Teste de contrato: consome todos os exemplos válidos e rejeita os inválidos (para a DLQ); a reentrega não duplica a resposta; os eventos emitidos validam contra os schemas | E2.1, E3.3 | Não |
| E3.5 | Consumidor de `cancel.requested.v1`: pára a geração e não inicia novas chamadas | código | Um cancelamento a meio da geração emite `turn.failed{reason: cancelled}` em menos de 2 s | E3.4 | Não |

## Épico E4: conversas no Laravel (FR-001, FR-002, FR-008, FR-009, FR-022; AC-03)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E4.1 | Spec de Conversations (`kai-spec`), incluindo a P-018 | spec | Spec aprovada; P-018 fechada | — | Sim |
| E4.2 | Tabelas `conversations`, `messages` e `missions` (mínima), `outbox` e `inbox`, com `user_id` e migrações reversíveis (`kai-db-migration`) | código | Os testes de migração sobem e descem; as queries filtram por `user_id` | E4.1 | Não |
| E4.3 | Endpoint `POST /conversations/{id}/messages`: persiste a mensagem e escreve o `turn.requested` no outbox na mesma transacção, com o `traceparent` | código | Teste de produtor: a mensagem gerada valida contra o schema; uma falha a meio não deixa a mensagem sem outbox, nem o contrário | E4.2 | Não |
| E4.4 | Relay do outbox para o RabbitMQ, com publisher confirms e span PRODUCER | código | Matar o relay a meio não perde nem duplica (at-least-once mais dedupe na inbox do Python) | E2.1, E4.3 | Não |
| E4.5 | Consumidor de eventos com inbox: `turn.completed`/`failed` (*first-wins*), `usage.recorded` para `model_usage`; dono derivado do registo do Laravel | código | Negativos: `user_id` de outro dono, `run_id` de outro turno e um segundo evento terminal são rejeitados e auditados (SPEC-003 §4) | E4.4 | Não |
| E4.6 | Autorização do canal privado do streaming (só o dono do `run`) | código | Negativos: outro utilizador, uma sessão revogada e um pedido de outra origem `localhost` não subscrevem; teste de arquitectura: todo o evento usa `PrivateChannel` (revisão do spike, ADR-0015) | E2.3, E4.2 | Sim |

## Épico E5: chat no Command Center (FR-001, FR-008; AC-03, AC-09)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E5.1 | Vista de conversa: enviar, ver os tokens a chegar, reconciliar com a resposta final (`delta_count`) | código | Vitest; E2E AC-03: os tokens aparecem incrementalmente e, depois de recarregar a página, a mensagem e a resposta estão lá | E4.3, E4.6 | Não |
| E5.2 | Estados explícitos e acessíveis (Processing, Error com o motivo e o `trace_id`) e botão de cancelar | código | E2E AC-09 (cancelar mostra Error com o motivo); `aria-live`; WCAG 2.2 AA | E5.1, E6.2 | Não |

## Épico E6: limites, custos e cancelamento (FR-050, NFR-011; AC-09; P-002)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E6.1 | Limites por turno (tokens, tempo, custo) enviados no `turn.requested` e aplicados no Python; tecto diário e kill switch no Laravel | código | Um turno que excede o orçamento termina em `FAILED` (`budget_exceeded`); com o tecto diário atingido, o Laravel recusa antes de publicar | E3.4, E4.5 | Não |
| E6.2 | Cancelamento pelo owner: a missão passa a `CANCELLED` no Laravel, que envia `cancel.requested` | código | AC-09 em integração e E2E | E3.5, E4.5 | Não |
| E6.3 | Mede custo e latência com o `fake` e com um modelo real (opcional, decisão do owner) e fecha a P-002 | medição | Valores registados em `analysis.md` com a evidência | E6.1 | Não |

## Épico E7: trace ponta a ponta e AC-10 (NFR-002, NFR-026; `observability.md`)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E7.1 | Instrumenta o Laravel (HTTP, outbox e relay, consumidor) e o Python (CONSUMER, `llm.generate`), com logs JSON correlacionados e sem conteúdo | código | Um pedido real dá um único trace React → Laravel → RabbitMQ → Python → LLM no Tempo | E2.2, E4.4, E3.4 | Não |
| E7.2 | Métricas RED por rota e consumidor, profundidade de fila e DLQ, tokens e custo (`kai_*`, sem `user_id` nas labels) | código | Dashboard mínimo versionado; alerta para a DLQ não vazia | E7.1 | Não |
| E7.3 | AC-10 na CI: E2E de conversa com o `fake`, sem rede nem chaves | teste | Job E2E verde na CI com a stack completa (com RabbitMQ e AI Engine) | E5.1, E3.4 | Não |

## Ordem e caminho crítico
1. **Caminho crítico:** E1.2 → E2.1 → E3.4 → E4.4 → E4.5 → E5.1 → E7.3.
2. **Em paralelo desde o início:** E1.1 → E1.4 → E2.3; E1.3 → E2.2; E3.1 → E3.2 → E3.3; E4.1 → E4.2 → E4.3.
3. **No fim:** E6, E5.2 e E7.1/E7.2.

## Riscos

| Risco | P/I | Mitigação | Liga a (§4.3) |
|---|---|---|---|
| O Reverb não aceita publicação a partir do Python | M/M | Spike primeiro (E1.1); fallback SSE já decidido no ADR-0009 | — |
| Duplicação ou perda de mensagens entre o outbox, o relay e a inbox | M/A | Testes de matar o processo a meio (E4.4); inbox nos dois lados; idempotência de negócio (SPEC-003) | — |
| Custo descontrolado com um modelo real | M/A | `fake` por omissão; limites por turno e tecto diário antes de qualquer chamada real (E6.1) | Custo descontrolado |
| Conteúdo de conversas em logs ou traces | M/A | Revisão de segurança por épico; teste que procura conteúdo de exemplo nos logs, como no E2E da E4.6b | Segredos ao fornecedor |
| Convenções OTel de messaging instáveis | M/B | Semconv fixada (E1.3) | Convenções OTel |
| A stack de dev e de CI fica pesada (RabbitMQ, LGTM, Reverb, AI Engine) | A/M | Cada serviço só entra com o critério que o exige; o `otel-lgtm` é opcional na CI se o trace for verificado por exportação para ficheiro (a decidir na E7.1) | Infra antes de valor |

## Verificação do milestone
- `scripts/ci/all.sh` verde no local e na CI, incluindo o novo job do AI Engine e o E2E de conversa com o `fake` (AC-10).
- E2E de AC-03 e de AC-09 a passar.
- Demo com dados sintéticos: uma conversa com streaming e um cancelamento, e o trace único aberto no Grafana (captura no PR).
- Revisões `kai-security-reviewer` e `kai-verifier` por épico.
- Documentação: ADR-0009 resolvido; ADR-0014 actualizado com o job do AI Engine; P-002, P-018 e P-019 fechadas; specs novas; `STATUS.md`.
