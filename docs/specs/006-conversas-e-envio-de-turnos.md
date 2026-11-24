# SPEC-006: Conversas e envio de turnos (Laravel)

- **Estado:** Aprovada (owner, 2026-11-24)
- **Data:** 2026-11-24
- **Milestone:** M03 (E4.1 → E4.2, E4.3, E4.4)
- **Autor:** Claude Code, para o owner
- **Requisitos:** FR-001, FR-002, FR-009, FR-022, FR-050, FR-051, FR-053 (subconjunto), FR-055, NFR-009, NFR-011, NFR-013, NFR-026; AC-03 (persistência)
- **ADRs relacionados:** ADR-0001, ADR-0002, ADR-0013 (máquina de estados da missão), ADR-0018 (outbox), ADR-0015
- **Continua em:** [SPEC-007](007-eventos-de-turno-e-canal.md) (eventos de volta, uso, canal de streaming)

## 1. Contexto
- **[C]** O AI Engine já consome `ai.conversation.turn.requested.v1` e devolve `turn.completed`, `turn.failed` e `usage.recorded` (E3.4a, SPEC-004). Falta o lado do Laravel, dono das conversas e da missão (ADR-0002: o Python não tem estado de negócio autoritativo).
- **[C]** O protótipo do chat (SPEC-005) fixou o que a UI precisa: enviar, receber `run_id` para o streaming, ver o estado e, depois de recarregar, o histórico.
- **[C P-018, fechada a 2026-11-23]** Um turno é uma missão de um passo; o Laravel envia sempre `mission_id`, e o cancelamento (E6.2) faz-se por ela.
- **[C SPEC-003 §6]** O tecto de 100 mensagens do contrato não é a política da janela de contexto: fica decidida aqui (P-025).

## 2. Objectivo
O owner tem conversas persistidas e isoladas. Cada mensagem que envia cria, numa só transacção, a mensagem, uma missão de um passo e o comando `turn.requested` no outbox, que chega ao AI Engine pelo RabbitMQ. Ao recarregar a página, vê a conversa como a deixou.

## 3. Decisões de comportamento [H]
1. **Conversa:** pertence a um `user_id`. O título é o início da primeira mensagem (até 80 caracteres), nunca gerado pelo LLM. Não se apaga no M03 (FR-025, M04).
2. **Mensagens append-only:** a do owner é escrita ao enviar. A do KAI só nasce quando chega o `turn.completed` (SPEC-007), uma única vez. Os deltas nunca são persistidos.
3. **Missão do turno:** criada na mesma transacção da mensagem. Percorre `PENDING → PLANNING → RUNNING` de imediato (um passo, sem planeamento), cada transição registada em `mission_events`, para respeitar o ADR-0013 sem uma excepção. Os estados terminais vêm da SPEC-007.
4. **Um turno de cada vez por conversa:** enquanto houver uma missão não terminal na conversa, um envio novo dá 409. O owner cancela (E6.2) ou espera.
5. **Idempotência do envio:** o cliente gera o `id` da mensagem (UUIDv7). Repetir o mesmo `id` com o mesmo conteúdo devolve a mesma resposta sem novo outbox; com conteúdo diferente, 409.
6. **Janela de contexto (P-025):** as últimas N mensagens concluídas da conversa (do owner e do KAI, sem as de turnos falhados), por ordem, mais a nova; corta pelas mais antigas até caber num tecto de caracteres.
7. **Limites do turno (P-002):** `max_output_tokens`, `timeout_seconds` e `max_cost_usd` vêm da configuração do Laravel, nunca do cliente. Valores provisórios até à E6.3.
8. **Outbox (ADR-0018):** a linha guarda o envelope v1 completo e o `traceparent`/`tracestate` do pedido HTTP. O relay (E4.4) publica-a com publisher confirms, routing key igual ao tipo e `user_id=kai-api`, marca-a como publicada e repete com backoff. É at-least-once: o AI Engine deduplica pelo `id` (AC-004-05).
9. **Rate limit (FR-050):** envios por utilizador por minuto, com 429. O tecto diário de custo e o kill switch ficam na E6.1.
10. **API para a SPA (P-027):** endpoints sob `/api`, com sessão Sanctum (como `/api/sessions`). O contrato fica em OpenAPI antes do código.

## 4. Critérios de aceitação
| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-006-01 | O owner autenticado | Cria uma conversa e depois lista as conversas | A lista tem só as suas, da mais recente para a mais antiga, com título e data | integração (Pest) |
| AC-006-02 | Uma conversa do owner, sem turno em curso | Envia uma mensagem válida | 202 com `user_message_id`, `run_id` e `mission_id`; na mesma transacção ficam a mensagem, a missão em `RUNNING` (com os 3 eventos de estado) e uma linha de outbox com um `turn.requested.v1` que valida contra o schema (teste de produtor) | integração, contrato |
| AC-006-03 | Uma falha a meio da transacção (ex.: a escrita do outbox falha) | O owner envia | Não fica nem a mensagem nem a missão nem o outbox; a resposta é 5xx sem detalhes | integração |
| AC-006-04 | Uma conversa com histórico, incluindo um turno falhado | O owner envia | O `messages` do comando tem só mensagens dessa conversa, por ordem, sem as do turno falhado, com a nova em último e dentro dos tectos da P-025 | unit, integração |
| AC-006-05 (negativo) | Uma conversa de outro utilizador, ou um id inexistente | O owner lista as mensagens ou envia | 404 igual nos dois casos; nada é escrito | integração (segurança) |
| AC-006-06 (negativo) | Um turno ainda em curso na conversa | O owner envia outra mensagem | 409; nada é escrito | integração |
| AC-006-07 | Um envio já aceite | O cliente repete o mesmo `id` (mesmo conteúdo / conteúdo diferente) | Mesma resposta e um só outbox / 409 | integração |
| AC-006-08 (negativo) | Conteúdo vazio, só espaços, com mais de 32 000 caracteres, ou campos extra (`user_id`, `limits`, `role`, `mission_id`) | O owner envia | 422 com erro por campo; os limites e o dono nunca vêm do cliente | integração (segurança) |
| AC-006-09 | Uma conversa com mensagens do owner e do KAI | O owner pede as mensagens (paginação por cursor) | Recebe-as por ordem, com o estado do turno (em curso, concluído, falhado com motivo e `trace_id`), igual depois de recarregar (AC-03) | integração, E2E (E5.1) |
| AC-006-10 | Linhas de outbox por publicar | O relay corre, é morto a meio e volta | Cada comando chega ao RabbitMQ pelo menos uma vez, com o `traceparent` guardado, e nenhuma linha fica por publicar; uma linha só é marcada depois do confirm | integração (RabbitMQ real) |
| AC-006-11 (negativo) | Mais envios por minuto do que o rate limit | O owner envia | 429 e nada é escrito | integração |

## 5. Segurança e privacidade
- **Níveis de operação:** enviar uma mensagem → nível 1 (conversa sem ferramentas; `tools` vai sempre vazio no M03).
- **Dados e isolamento:** `conversations`, `messages`, `missions`, `mission_events` e `outbox` com `user_id`; toda a query filtra por ele (FR-051) e um recurso de outro dono dá 404, não 403.
- **Conteúdo não confiável:** as mensagens do owner vão para o prompt como `user` (SPEC-004 §3.8). As do KAI (SPEC-007) são output do LLM: guardadas e devolvidas como texto, nunca interpretadas.
- **Ameaças:** IDOR em conversas e mensagens (AC-006-05); *mass assignment* do dono ou dos limites (AC-006-08); abuso de custo por envio em ciclo (AC-006-06, 11; tecto diário na E6.1); envenenamento do contexto com mensagens de outra conversa (AC-006-04).
- **Segredos:** nenhum novo. O relay usa a password `kai-api` do RabbitMQ já existente (ADR-0018).
- **Logs:** IDs, contagens e tamanhos; nunca o conteúdo das mensagens (NFR-013).

## 6. Observabilidade
- **Spans:** o HTTP do envio (com `traceparent` aceite do cliente); `publish kai.commands` (PRODUCER) no relay, filho do span do pedido através do contexto guardado no outbox.
- **Métricas:** `kai_http_server_duration_seconds` por rota; `kai_outbox_pending_messages`; `kai_outbox_publish_total{outcome}`; `kai_conversation_turns_total{outcome}` (sem `user_id`).
- **Logs:** `turn_requested{conversation_id, mission_id, run_id, message_id, context_messages, context_chars}`, `outbox_published`, `outbox_publish_failed`.

## 7. Contratos
- **AsyncAPI:** nenhum alterado; o `turn.requested.v1` já existe.
- **OpenAPI novo para a SPA (P-027):** `GET/POST /api/conversations`, `GET /api/conversations/{id}/messages`, `POST /api/conversations/{id}/messages`. Escrito com a skill `kai-contract` na E4.3, antes do código, com aprovação do owner.

## 8. Plano de testes
- **Unit:** janela de contexto (ordem, corte, exclusões); máquina de estados da missão (só as transições do ADR-0013).
- **Integração (Pest, SQLite em memória):** AC-006-01 a 09 e 11.
- **Contrato:** o comando gerado valida contra `packages/contracts` (produtor), e cada exemplo `valid/` do `turn.requested` é reprodutível a partir do domínio.
- **Integração com o RabbitMQ real** (`scripts/ci/integration.sh`): AC-006-10.
- **Arquitectura:** o módulo de Conversations não lê tabelas de outros módulos (ADR-0001).

## 9. Fora de âmbito
- Consumo dos eventos de volta, `model_usage` e canal do Reverb: [SPEC-007](007-eventos-de-turno-e-canal.md).
- Cancelamento pelo owner (E6.2), tecto diário e kill switch (E6.1).
- Apagar, renomear ou exportar conversas (FR-025, FR-052, M04).
- Anexos, ferramentas, memória de longo prazo e RAG.
- Ligação da UI (E5.1).

## 10. Perguntas abertas
| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-025 | Política da janela de contexto no M03 | **Fechada (owner, 2026-11-24):** últimas **20** mensagens concluídas, cortadas pelas mais antigas até **48 000 caracteres** no total (cerca de 12 000 tokens), mais a nova. Medida e revista na E6.3 | Não (fechada) |
| P-026 | Valores provisórios dos limites por turno (P-002) | **Fechada (owner, 2026-11-24):** `max_output_tokens` 1024, `timeout_seconds` 60, `max_cost_usd` 0,25; rate limit de 10 envios por minuto. Ficam em configuração e são medidos na E6.3 | Não (fechada) |
| P-027 | Contrato da API da SPA | **Fechada (owner, 2026-11-24):** OpenAPI `packages/contracts/openapi/public-v1.yaml` com a skill `kai-contract`, validado na CI como o interno, antes do código da E4.3. Os tipos TypeScript gerados a partir dele (regra `react-typescript.md`) ficam para o E5.1, porque pedem uma dependência nova | Não (fechada) |
