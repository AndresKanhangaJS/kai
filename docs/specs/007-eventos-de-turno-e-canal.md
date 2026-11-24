# SPEC-007: Eventos de turno, uso e canal de streaming (Laravel)

- **Estado:** Aprovada (owner, 2026-11-24)
- **Data:** 2026-11-24
- **Milestone:** M03 (E4.1 → E4.5, E4.6)
- **Autor:** Claude Code, para o owner
- **Requisitos:** FR-008, FR-022, FR-051, FR-055, FR-058, NFR-002, NFR-009, NFR-011, NFR-017, NFR-026, NFR-028; AC-03, AC-09
- **ADRs relacionados:** ADR-0002, ADR-0013, ADR-0015, ADR-0018
- **Continua:** [SPEC-006](006-conversas-e-envio-de-turnos.md)

## 1. Contexto
- **[C SPEC-004]** Para cada `turn.requested`, o AI Engine emite exactamente um `turn.completed` ou um `turn.failed`, e um `usage.recorded` por chamada ao fornecedor, para `kai.events` (fila `kai-api.events`).
- **[C SPEC-003 §4]** O dono nunca é confiado: os IDs dos eventos servem só para lookup; o Laravel deriva o dono e as ligações do seu registo e rejeita divergências, com auditoria. O estado terminal é *first-wins*.
- **[C ADR-0015]** Os deltas vão pelo Reverb, no canal `private-run.{run_id}`; só o dono do run subscreve, e a decisão é do Laravel em `/broadcasting/auth` (E4.6).

## 2. Objectivo
As respostas e as falhas do KAI ficam persistidas uma única vez, a missão do turno termina no estado certo, o custo de cada chamada fica registado, e só o owner consegue ouvir o streaming do seu turno.

## 3. Decisões de comportamento [H]
1. **Consumidor de `kai-api.events`** (ADR-0016, cliente PHP aprovado): só aceita o `user_id` AMQP `kai-ai-engine`, valida envelope e payload contra o schema e a routing key igual ao tipo; o inválido vai para a DLQ sem efeito.
2. **Inbox (dedupe):** tabela `inbox` com o `id` do envelope, na mesma transacção do efeito. Uma reentrega já aplicada é confirmada sem efeito.
3. **Dono derivado:** o turno encontra-se pelo `run_id`. O `user_id`, a `conversation_id` e o `user_message_id` do evento têm de coincidir com o registo; uma divergência vai para a DLQ e é auditada, sem efeito.
4. **`turn.completed`:** cria a mensagem do KAI com o `assistant_message_id` e o `content` (texto não confiável, até 100 000 caracteres), e a missão passa a `COMPLETED`, na mesma transacção. `finish_reason: max_output_tokens` fica guardado (a UI mostra "resposta cortada").
5. **`turn.failed`:** a missão passa a `FAILED`, ou a `CANCELLED` se o motivo for `cancelled`, com o motivo, o código e a mensagem segura e o `trace_id`; nenhuma mensagem do KAI é criada.
6. **First-wins:** um segundo evento terminal para o mesmo turno (com `id` diferente) é confirmado sem efeito e auditado (`turn_terminal_ignored`).
7. **`usage.recorded`:** uma linha em `model_usage` por `usage_id` (idempotente), com o dono derivado do run, o fornecedor, o modelo, os tokens, o custo (decimal, nunca float) e a latência. Um `usage.recorded` tardio de um turno já terminado é registado: a chamada custou.
8. **Vigia de turnos órfãos:** uma missão de turno em `RUNNING` sem evento terminal depois de `timeout_seconds` + 120 s passa a `FAILED` (`timeout`, código `turn_orphaned`) e é auditada. Um evento terminal que chegue depois é ignorado pelo first-wins.
9. **Canal privado (E4.6):** `/broadcasting/auth` autoriza `private-run.{run_id}` só à sessão autenticada do dono da missão desse run, e só enquanto a missão não for terminal há mais de 10 minutos. Todo o evento do KAI usa `PrivateChannel`.
10. **Auditoria:** no mesmo canal de log de auditoria da SPEC-002 (eventos estruturados, só IDs); a tabela `audit_logs` (NFR-002) fica para quando o módulo Audit existir [P].

## 4. Critérios de aceitação
| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-007-01 | Um turno em `RUNNING` | Chega um `turn.completed` válido | A mensagem do KAI fica persistida com o conteúdo e o `finish_reason`, a missão passa a `COMPLETED`, e o evento entra na inbox, tudo na mesma transacção | integração |
| AC-007-02 | Um turno em `RUNNING` | Chega um `turn.failed` (`timeout`, `budget_exceeded`, `provider_unavailable`, `cancelled`) | A missão termina em `FAILED` (ou `CANCELLED`) com o motivo, a mensagem segura e o `trace_id`, que a API de mensagens devolve (AC-09); nenhuma mensagem do KAI | integração |
| AC-007-03 | Um evento já aplicado | É reentregue (mesmo `id`) | É confirmado sem efeito; uma só mensagem do KAI | integração |
| AC-007-04 (negativo) | Um turno já terminado | Chega outro evento terminal com `id` diferente | Sem efeito; `turn_terminal_ignored` auditado | integração |
| AC-007-05 (negativo) | Eventos com `user_id` de outro dono, `run_id` desconhecido, ou `conversation_id`/`user_message_id` que não batem com o run | São consumidos | Vão para a DLQ sem efeito e cada um é auditado | integração (segurança) |
| AC-007-06 (negativo) | Um evento publicado por outro utilizador AMQP (`kai-api`, `kai-admin`), sem `user_id`, inválido no schema ou com a routing key errada | É consumido | Vai para a DLQ sem efeito | integração (RabbitMQ real) |
| AC-007-07 | `usage.recorded` de um turno (incluindo um que chegue depois do terminal) | É consumido duas vezes | Uma só linha em `model_usage`, com o dono do run e o custo em decimal | integração |
| AC-007-08 | Um turno em `RUNNING` sem evento terminal | Passam `timeout_seconds` + 120 s | A missão passa a `FAILED` (`turn_orphaned`), auditado; o owner pode voltar a enviar | integração (tempo controlado) |
| AC-007-09 (negativo) | O canal `private-run.{run_id}` | Pedem autorização: outro utilizador, uma sessão revogada, um pedido sem sessão, um run terminal há mais de 10 minutos | Todos recusados (403); só o dono, com sessão válida, é autorizado | integração (segurança) |
| AC-007-10 | O código de broadcasting do KAI | O teste de arquitectura corre | Todo o evento de broadcast usa `PrivateChannel` (ADR-0015) | arquitectura |
| AC-007-11 | Os dois lados ligados (stack `kai-it`) | Um envio real do owner passa pelo outbox, pelo AI Engine com o `fake` e volta | A resposta fica persistida, a missão `COMPLETED`, uma linha em `model_usage`, e o mesmo `trace_id` atravessa os dois serviços | integração ponta a ponta |

## 5. Segurança e privacidade
- **Níveis de operação:** nenhuma acção do owner; o consumidor aplica efeitos de nível 1 (persistir a resposta).
- **Dados e isolamento:** `messages`, `missions`, `mission_events`, `model_usage` e `inbox` com `user_id` derivado do registo, nunca do evento.
- **Conteúdo não confiável:** o `content` do `turn.completed` e a `message` do erro vêm do Python, o componente mais exposto a *prompt injection*: guardados como texto, com tecto de tamanho, nunca interpretados nem usados para decidir estado ou permissões.
- **Ameaças:** forjar eventos (AC-007-06, só `kai-ai-engine` publica em `kai.events`); escrever na conversa de outro dono com IDs trocados (AC-007-05); reescrever uma resposta já final (AC-007-04); ouvir o streaming de outro (AC-007-09); custos não registados (AC-007-07).
- **Segredos:** nenhum novo. A password `kai-api` do RabbitMQ e o segredo do Reverb já existem.

## 6. Observabilidade
- **Spans:** um CONSUMER por evento (`process kai-api.events`), filho do `traceparent` do evento.
- **Métricas:** `kai_consumer_messages_total{type,outcome}`, `kai_llm_tokens_total{direction}`, `kai_llm_cost_usd_total`, `kai_mission_outcomes_total{state}`, `kai_turns_orphaned_total`, `kai_queue_dlq_messages`.
- **Logs:** `turn_event_applied`, `turn_event_rejected{reason}`, `turn_terminal_ignored`, `turn_orphaned`, `channel_auth_denied`; só IDs.

## 7. Contratos
Nenhum alterado. Usa `turn.completed.v1`, `turn.failed.v1` e `usage.recorded.v1` (SPEC-003). A rota `/broadcasting/auth` é a do Laravel e não entra no OpenAPI.

## 8. Plano de testes
- **Unit:** derivação do dono; first-wins; transições terminais do ADR-0013.
- **Integração (Pest):** AC-007-01 a 05 e 07 a 09, com eventos gerados dos exemplos `valid/` dos contratos.
- **Integração com o RabbitMQ real e o AI Engine** (`scripts/ci/integration.sh`): AC-007-06 e AC-007-11.
- **Arquitectura:** AC-007-10.

## 9. Fora de âmbito
- Cancelamento pedido pelo owner (E6.2), tecto diário e kill switch (E6.1).
- A ligação da UI aos eventos e ao canal (E5.1).
- A tabela `audit_logs` e o ecrã de auditoria.
- Reprocessamento da DLQ (operação manual, `rabbitmq.md`).

## 10. Perguntas abertas
| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-028 | Margem do vigia de turnos órfãos e janela do canal depois do fim | 120 s depois do `timeout_seconds`; o canal fica autorizado até 10 minutos depois do fim do turno, para a UI reconciliar | Não |
