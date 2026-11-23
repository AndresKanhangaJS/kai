# SPEC-004: AI Engine mínimo (turno de conversa)

- **Estado:** Aprovada (owner, 2026-11-23, com as recomendações da §10)
- **Data:** 2026-11-23
- **Milestone:** M03 (E3.1; cobre E3.2–E3.5)
- **Autor:** Claude Code, para aprovação do owner
- **Requisitos:** FR-008, FR-009, FR-010, NFR-006, NFR-007, NFR-009, NFR-011, NFR-013, NFR-017, NFR-026, NFR-027, NFR-028; AC-03, AC-09, AC-10 (`docs/product/analysis.md`)
- **ADRs relacionados:**
  - ADR-0001, ADR-0002 (fronteira: o Python propõe e reporta, o Laravel decide e persiste);
  - ADR-0006 (`LLMGateway`); ADR-0010 (rede privada, um utilizador RabbitMQ por serviço);
  - ADR-0015 (deltas pelo Reverb); ADR-0016 (`aio-pika`); ADR-0017 (OpenTelemetry);
  - ADR-0018 (retry no consumidor, DLQ pelo broker);
  - SPEC-003 (contratos v1).

## 1. Contexto
- **[C analysis.md §7, M03]** O M03 introduz o `apps/ai-engine`: o LLM Gateway e a conversa em streaming. Critério do milestone: AC-03, AC-09, AC-10 e um trace de ponta a ponta.
- **[C ADR-0002, SPEC-003 §2]** O Python não lê a BD do Laravel.
  - O `ai.conversation.turn.requested.v1` traz a janela de contexto e os limites do turno.
  - O Python responde com `turn.completed`/`turn.failed` e `usage.recorded`.
  - O Laravel é o único que muda o estado do turno ou da missão (*first-wins*).
- **[C ADR-0015]** Os deltas são efémeros:
  - vão para `private-run.{run_id}` pela API HTTP do Reverb, agregados por cerca de 50 ms e com `seq`;
  - não passam pelo RabbitMQ;
  - o cliente reconcilia pelo `delta_count` do `turn.completed`.
- **[C ADR-0018]** Retry em memória no consumidor. `nack` sem requeue → DLQ. Crash → DLQ ao fim de 5 entregas.
- **[C ADR-0006, P-015]** Adaptadores `fake` (por omissão), Anthropic e Ollama. A CI usa só o `fake`.
- **[C E2.1]** A topologia já existe: o `kai-ai-engine` lê `ai-engine.commands` e só escreve em `kai.events`, com os tipos permitidos pelas topic permissions.

## 2. Objectivo
O owner envia uma mensagem e o AI Engine gera a resposta com o modelo configurado. A resposta chega em streaming e termina sempre num evento final (concluído ou falhado, com o motivo). Os limites do turno são respeitados, o cancelamento é obedecido em segundos e não sai conteúdo para logs ou traces.

## 3. Decisões de comportamento [H]
1. **Uma mensagem, um turno, um estado final.** Para cada `turn.requested` aceite, o Python emite exactamente um `turn.completed` ou um `turn.failed`, mais no máximo um `usage.recorded` por chamada ao fornecedor. Só faz `ack` depois dos publisher confirms desses eventos.
2. **Validar antes de gastar.** O Python valida tudo antes de chamar o modelo, e uma mensagem que falhe qualquer validação vai para a DLQ (`nack`) sem chamada ao LLM nem evento. Valida:
   - o schema (envelope e payload);
   - o `user_id` AMQP, que tem de ser `kai-api`;
   - o `producer`;
   - `tools` vazio ou ausente, porque as ferramentas só chegam no M05.
3. **Retry só antes do primeiro delta.** Uma falha transitória do fornecedor antes do primeiro delta repete com backoff e jitter, dentro do `timeout_seconds`. Depois do primeiro delta não há retry, para não duplicar texto no ecrã: o turno termina em `turn.failed` (`provider_error`).
4. **Falhas de negócio não vão para a DLQ.** Timeout, orçamento, cancelamento e fornecedor em baixo dão `turn.failed` com o motivo, e a mensagem é confirmada. Para a DLQ vai só o que é inválido ou o que não se consegue reportar (o RabbitMQ não confirma os eventos).
5. **Deltas são *best effort*.** Uma falha a publicar no Reverb não falha o turno: a resposta completa chega no `turn.completed`.
6. **Limites:**
   - **`max_output_tokens`** vai para o fornecedor. Se for atingido, o turno é `turn.completed` com `finish_reason: max_output_tokens`.
   - **`max_cost_usd`:** o custo estimado da entrada (`count_tokens`) mais o máximo da saída, à tabela de preços versionada do modelo, é verificado **antes** da chamada; se exceder, dá `turn.failed` (`budget_exceeded`) sem chamar o fornecedor. Com o `fake`, o custo é 0.
   - **`timeout_seconds`:** conta desde a recepção da mensagem; ao expirar, a geração é interrompida.
7. **Cancelamento:** `ai.mission.cancel.requested.v1` interrompe a geração do turno ligado a essa `mission_id`, se existir neste processo, e não inicia novas chamadas. Um cancelamento para uma missão desconhecida é confirmado sem efeito. O estado final é do Laravel (SPEC-003 §4).
8. **Modelo e prompt:**
   - o fornecedor e o modelo vêm da configuração do serviço (`MODEL_PROVIDER`, por omissão `fake`), nunca da mensagem;
   - o prompt de sistema é versionado no repositório (ADR-0006);
   - as mensagens do owner entram no prompt como mensagens de utilizador, nunca como instruções de sistema.
9. **Rede:** sem porta publicada no host (ADR-0010). Redes `default` (RabbitMQ, Reverb) e `telemetry` (OTLP).

## 4. Critérios de aceitação
| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-004-01 | O AI Engine a correr | Pergunto por `/health/live` e `/health/ready` | `live` dá 200 enquanto o processo responde; `ready` dá 200 só com a ligação ao RabbitMQ e o consumidor activos, e 503 caso contrário. As respostas validam contra `health.v1` | integração |
| AC-004-02 (AC-03) | O fornecedor `fake` e um `turn.requested.v1` válido do `kai-api` | O Python o consome | No `private-run.{run_id}` chegam deltas com `seq` 1..n contíguo; depois sai um `turn.completed.v1` cujo `content` é a concatenação dos deltas e cujo `delta_count` é n, e um `usage.recorded.v1`. Os eventos validam contra os schemas, levam o `user_id` AMQP `kai-ai-engine` e o `causation_id` do comando, e a mensagem só é confirmada depois dos publisher confirms | integração |
| AC-004-03 (AC-10) | A suite do `apps/ai-engine` | Corre num contentor sem rede e sem chaves de fornecedor | Os testes unitários e de contrato passam só com o `fake`; um adaptador real pedido sem chave falha no arranque com erro claro, nunca em runtime | unit, CI |
| AC-004-04 (negativo) | Cada exemplo `invalid/` de `turn.requested`, ou um válido publicado com `user_id` AMQP diferente de `kai-api`, `producer` errado ou `tools` não vazio | O Python o recebe | Vai para a `ai-engine.commands.dlq` (`x-death` `rejected`), sem chamada ao LLM, sem deltas e sem eventos; um log `message_rejected` com o motivo e o `id`, sem conteúdo | contrato, integração |
| AC-004-05 | Um `turn.requested` já processado (mesmo `id` de envelope) | É entregue de novo | Não há segunda chamada ao fornecedor nem eventos novos; a mensagem é confirmada (inbox) | integração |
| AC-004-06 (AC-09) | Um turno com o `fake` mais lento do que o `timeout_seconds` | O tempo expira | A geração é interrompida, sai `turn.failed.v1` com `reason: timeout` e um `usage.recorded` com os tokens consumidos; não há `turn.completed` | integração |
| AC-004-07 (AC-09, negativo) | Um turno cujo custo estimado excede o `max_cost_usd` (tabela de preços de teste) | O Python o avalia | Sai `turn.failed.v1` com `reason: budget_exceeded`, **sem** chamada ao fornecedor, sem deltas e sem `usage.recorded` | unit, integração |
| AC-004-08 (AC-09) | Um turno em geração, ligado a uma `mission_id` | Chega `ai.mission.cancel.requested.v1` para essa missão | Em menos de 2 s a geração pára, não há novas chamadas ao fornecedor e sai `turn.failed.v1` com `reason: cancelled`; um cancelamento para uma missão desconhecida é confirmado sem efeito | integração |
| AC-004-09 | O fornecedor falha de forma transitória antes do primeiro delta, ou depois dele | O Python trata a falha | Antes: repete com backoff e jitter dentro do timeout; se continuar a falhar, sai `turn.failed` (`provider_unavailable`) e a mensagem é confirmada. Depois: sem retry, sai `turn.failed` (`provider_error`) | unit, integração |
| AC-004-10 | O Reverb indisponível | Um turno corre | O turno termina em `turn.completed` com o conteúdo completo; a falha conta em `kai_stream_publish_failures_total` | integração |
| AC-004-11 (negativo, NFR-013) | Um turno cujas mensagens e resposta contêm uma string-canário sintética | Corre do início ao fim | O canário não aparece em nenhum log, span ou métrica; o span CONSUMER é filho do `traceparent` do comando e o evento emitido leva um `traceparent` novo do mesmo trace | integração |

## 5. Segurança e privacidade
- **Níveis de operação:** gerar uma resposta de conversa é **nível 1** (consulta), sem aprovação. Não há ferramentas no M03: `tools` não vazio é recusado (AC-004-04).
- **Dados tocados e isolamento:**
  - o Python não tem BD de negócio;
  - o `user_id` do payload viaja só para correlação e é devolvido nos eventos; o Laravel deriva o dono e rejeita divergências (SPEC-003 §4);
  - a inbox guarda só IDs de mensagem e estado, nunca conteúdo (P-020).
- **Conteúdo não confiável:**
  - a resposta do LLM é não confiável: o Python não age sobre ela no M03, só a reencaminha, limitada pelo schema;
  - as mensagens antigas com `role: assistant` (output anterior do LLM) entram como mensagens de assistente, nunca como sistema;
  - **ameaças:** prompt injection a tentar mudar o modelo ou os limites é ineficaz, porque nenhum dos dois vem do prompt nem da mensagem.
- **Abuso de custo:**
  - o tecto por turno é verificado antes da chamada (AC-004-07);
  - o tecto diário e o kill switch ficam no Laravel (E6.1);
  - um comando forjado é impossível sem as credenciais do `kai-api`, porque o broker valida o `user_id` (E2.1).
- **Segredos:** vêm só de variáveis de ambiente e nunca aparecem em logs, spans, mensagens ou `/health`:
  - `KAI_RABBITMQ_AI_ENGINE_PASSWORD`;
  - o segredo da app do Reverb;
  - `ANTHROPIC_API_KEY` (opcional);
  - o URL do Ollama, configurado pelo owner.
- **Modelo de ameaças:** o fluxo é de nível 1 sem ferramentas, por isso basta a análise acima. A `kai-threat-model` corre no M05, com ferramentas.

## 6. Observabilidade
- **Spans:**
  - `process ai-engine.commands` (CONSUMER, filho do `traceparent`);
  - `llm.generate`, com os atributos `gen_ai.*` da semconv 1.44.0 (fornecedor, modelo, tokens, `finish_reason`) e `kai.prompt.version`;
  - `publish kai.events` (PRODUCER);
  - `stream.publish` por lote de deltas, agregado no span pai se o volume o justificar.
- **Métricas:**
  - `kai_llm_tokens_total{direction}`;
  - `kai_llm_cost_usd_total`;
  - `kai_llm_request_duration_seconds{provider,outcome}`;
  - `kai_llm_time_to_first_token_seconds{provider}`;
  - `kai_consumer_messages_total{queue,outcome}`, com o outcome `completed|failed|rejected|duplicate`;
  - `kai_turn_failures_total{reason}`;
  - `kai_stream_publish_failures_total`.
  - Sem `user_id` nem IDs nos labels.
- **Logs:** JSON com `trace_id`, `span_id`, `service`, `level` e `event`. Eventos: `turn_started`, `turn_completed`, `turn_failed`, `message_rejected` e `provider_retry`. Levam só IDs, contagens, códigos e durações, nunca conteúdo.
- **NFR-017:** o modelo, a versão do prompt, os tokens, o custo, a latência e o `trace_id` ficam registados no span `llm.generate` e no `usage.recorded`. A versão do prompt vai só no span, porque o contrato v1 não tem esse campo (P-022).

## 7. Contratos
Usa os contratos v1 (SPEC-003) sem alterações:
- consome `ai.conversation.turn.requested.v1` e `ai.mission.cancel.requested.v1`;
- produz `ai.conversation.turn.completed.v1`, `ai.conversation.turn.failed.v1` e `ai.model.usage.recorded.v1`;
- responde em `GET /health/live` e `GET /health/ready` (`health.v1`).

O evento de delta do Reverb (`{seq, text}`) não está em `packages/contracts`: foi validado no spike (ADR-0015) e passa a schema na E2.3.

## 8. Plano de testes
- **Unitários (pytest, `fake`):**
  - validação e recusa;
  - cálculo do custo e verificação do orçamento;
  - agregação de deltas e `seq`;
  - decisão de retry antes e depois do primeiro delta;
  - mapeamento de erros para o `reason`.
- **Contrato:** todos os exemplos `valid/` de `turn.requested` e `cancel.requested` são aceites e todos os `invalid/` recusados. Cada evento produzido valida contra o seu schema, com os mesmos ficheiros que o lado PHP usa.
- **Integração (`scripts/ci/integration.sh`, stack `kai-it`):** RabbitMQ, Reverb e otel-lgtm reais, com o `fake` configurável (latência, falhas injectadas, canário); cobre AC-004-01, 02, 04 a 06 e 08 a 11.
- **Qualidade:** `scripts/ci/ai-engine.sh` com ruff, mypy (strict) e pytest, num contentor sem rede para os testes (AC-004-03).
- **E2E:** fica para a E7.3 (AC-10 com a stack completa).
- **Fixtures:** todas sintéticas. Nenhum teste usa rede externa ou chaves; os adaptadores Anthropic e Ollama são testados com respostas gravadas, sem rede.

## 9. Fora de âmbito
- Ferramentas, grants, `step.reported`/`step.resume` (M05).
- RAG, embeddings, `retrieval/search` (M04).
- Persistência, estados da missão, tecto diário e kill switch (Laravel, E4 e E6).
- A UI e a reconciliação dos deltas no cliente (E5).
- O NFR-015 (tempo até ao 1.º token medido no cliente) e as avaliações (E6.3 e M05).
- Escolher modelo por pedido.
- Várias réplicas do AI Engine (cancelamento entre processos).

## 10. Perguntas abertas
| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-018 | Um turno é uma missão de um passo no M03? | **Fechada (2026-11-23): sim.** O Laravel envia sempre `mission_id` no `turn.requested`, e o cancelamento faz-se por essa `mission_id` (fecha na E4.1) | Não (fechada) |
| P-020 | Onde guarda o Python a inbox (AC-004-05)? | **Fechada (2026-11-23):** Redis do Compose, com `SET NX` em `inbox:ai-engine:{id}` e TTL de 7 dias, só com IDs e estado, e um utilizador ACL próprio. Alternativa: sem inbox no Python, com o *first-wins* do Laravel a absorver duplicados, à custa de gerar e pagar duas vezes. Pede `redis-py` (dependência nova) | Não (fechada) |
| P-021 | Dependências do `apps/ai-engine` | Python 3.14 (imagem por digest), FastAPI, uvicorn, `aio-pika` 10.2.3 (ADR-0016), `jsonschema`, `httpx` (Reverb e Ollama), SDK `anthropic`, OpenTelemetry (ADR-0017), pytest, ruff e mypy. Versões com ≥ 14 dias e com hashes; a aprovação é pedida em lista na E3.2 e na E3.3 | Sim, a E3.2 |
| P-022 | `prompt_version` no `usage.recorded` (NFR-017) | Fica só no span no M03; se a auditoria de custos precisar, junta-se como campo opcional (compatível, mesma major) | Não |
| P-002 | Valores dos limites (tokens, timeout, custo) | Ficam no Laravel (E6.1), medidos com o conjunto de avaliação; o AI Engine só aplica os do comando | Não |
