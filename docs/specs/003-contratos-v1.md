# SPEC-003: Contratos v1 Laravel ↔ Python

- **Estado:** Aprovada (2026-11-22, autorização geral do owner para a sessão)
- **Data:** 2026-11-22
- **Milestone:** M02 (E3.1, E3.2, E3.3 e E2.3)
- **Autor:** Claude Code (`kai-spec`, `kai-contract`)
- **Requisitos:** FR-032 (subconjunto), NFR-001, NFR-006, NFR-009, NFR-011
- **ADRs relacionados:** ADR-0002 (fronteira), ADR-0018 (mensageria; substitui o ADR-0003), ADR-0009 (streaming), ADR-0010 (autenticação entre serviços), ADR-0013 (modelo de segurança)

## 1. Contexto
- **[C `analysis.md` §5.5]** Catálogo: síncrono `POST /internal/v1/tool-authorizations`, `/health/live`, `/health/ready`; assíncrono, as 6 mensagens do MVP com envelope comum.
- **[C ADR-0002]** O Laravel é o único escritor de missões, aprovações, auditoria e memórias; não há tabelas partilhadas. O Python propõe e reporta por eventos.
- **[C ADR-0009]** Os deltas de streaming vão pelo Reverb (`run.{id}`), não pelo RabbitMQ; a resposta final vem no `turn.completed`.
- **[C ADR-0013]** O nível e o modo de uma ferramenta vêm do Tool Registry, nunca do Python nem do LLM.
- O RabbitMQ e o AI Engine só chegam no M03. Esta spec define os contratos **antes** do código (regra de ouro 7); os testes de produtor e consumidor nascem com o código, no M03 e M05.

## 2. Decisões de desenho
1. **[H] Contexto no comando.** Como o Python não lê a BD do Laravel, o `ai.conversation.turn.requested.v1` leva a janela de contexto (até 100 mensagens, cada uma com até 32 000 caracteres). É conteúdo do owner, mas não é segredo: vai por rede privada e **nunca** é escrito em logs nem spans (`observability.md`). Alternativa rejeitada: um endpoint síncrono para o Python ler o contexto (mais uma ida e volta e mais uma superfície de API).
2. **[C ADR-0013] O execution grant nunca vai no RabbitMQ.** O Python obtém-no sempre em `POST /internal/v1/tool-authorizations`. Depois de uma aprovação, o `ai.mission.step.resume.v1` só diz qual passo retomar; o Python volta a pedir a autorização e recebe `allow`.
3. **O pedido de autorização não traz nível nem modo.** O Laravel deriva-os do Registry e recalcula o `arguments_sha256` sobre o JSON canónico (RFC 8785) dos argumentos.
4. **IDs:** UUID (v7 no `id` do envelope) para mensagens e entidades novas; `user_id` é inteiro (chave da tabela `users`). Valores monetários vão como string decimal, para evitar erros de vírgula flutuante.
5. **Producers:** `kai-api` (Laravel) e `kai-ai-engine` (Python). Cada tipo tem um só produtor válido.
6. **[C ADR-0013, revisão de segurança da E3] O taint é derivado só pelo Laravel.** Cada ferramenta do Tool Registry tem `ingests_external_content`. Ao emitir um grant de uma ferramenta destas, o Laravel marca a missão como *tainted* na mesma transacção, antes de devolver o `allow`. A partir daí, o nível ≥ 4 exige aprovação. Nenhum contrato leva `tainted`: um booleano vindo do Python (o componente mais exposto a *prompt injection*) e entregue de forma assíncrona deixaria o PDP decidir com dados atrasados ou forjados.
7. **Grant e aprovação de uso único.**
   - No máximo um grant por (`mission_id`, `step_id`, `arguments_sha256`). A aprovação é consumida quando o grant é emitido. Um pedido repetido recebe `deny` `step_already_authorized`, nunca o grant anterior.
   - Uma aprovação pendente por (`mission_id`, `step_id`): o mesmo pedido devolve o mesmo `approval_id`; args diferentes recebem `deny` `approval_pending_for_step`.
   - Há um tecto de passos e de pedidos por missão (`step_budget_exceeded`, `rate_limited` ou 429), contra a fadiga de aprovações.
8. **Limites de tamanho.** `arguments` e `output` são valores JSON com profundidade ≤ 4, strings ≤ 8000, arrays ≤ 100, objectos ≤ 50 chaves e inteiros seguros (±2^53−1, coerentes com o RFC 8785 nos dois lados).

## 3. Critérios de aceitação

| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-C1 | Os ficheiros de `packages/contracts` | A CI corre `scripts/ci/contracts.sh` | Cada JSON Schema é válido em draft 2020-12; o OpenAPI é válido em 3.1; o AsyncAPI referencia só schemas que existem | contrato (CI) |
| AC-C2 | Cada mensagem e cada corpo de pedido/resposta | Valido os seus exemplos `valid/` | Todos passam, contra o envelope e contra o payload | contrato (CI) |
| AC-C3 | Os exemplos `invalid/` (campo extra, obrigatório em falta, formato ou limite violado) | Valido-os | Todos falham; um exemplo inválido que passe faz a CI falhar | contrato (CI), negativo |
| AC-C4 | Um pedido de autorização com `level`, `mode`, `grant`, `tainted` ou `user_id` | É validado | É rejeitado pelo schema (`additionalProperties: false`): o Python não escolhe nível, dono nem taint | contrato, negativo de segurança |
| AC-C5 | Qualquer mensagem do RabbitMQ | O validador a analisa, seguindo os `$ref` | Não há nenhum campo para tokens, grants ou credenciais nem objectos abertos fora da allowlist; o `user_id` é obrigatório no payload (NFR-009). O validador testa-se a si próprio com schemas maus | contrato, negativo de segurança |

## 4. Segurança e privacidade
- Exemplos e fixtures com dados sintéticos; o scan de segredos da CI corre também sobre `packages/contracts`.
- Texto livre vindo do LLM ou de ferramentas (`content`, `output`) é não confiável. O schema limita-lhe o tamanho, mas não o torna seguro: o Laravel trata-o como dados.
- `traceparent` e `tracestate` seguem o formato W3C (sem CR/LF); os erros levam só um `code` e uma mensagem segura, nunca stack traces.
- **Dono derivado, nunca confiado.** Nos eventos Python → Laravel e no pedido de autorização, `user_id`, conversa, run, missão e passo servem só para lookup. O Laravel deriva o dono e as ligações do seu próprio registo e rejeita qualquer divergência, para a DLQ ou com 422/404, sempre com auditoria. Testes de consumidor (M03/M05): `user_id` de outro dono, `run_id` de outro turno, `step_id` de outra missão.
- **`tool-authorizations` não é *tolerant reader*:** qualquer campo fora do schema dá 422; nunca há *mass assignment* do corpo.
- O `grant` está marcado `x-kai-sensitive` e a resposta leva `Cache-Control: no-store`. O PEP-2 usa o `exp` do JWS (o `expires_at` é informativo) e só aceita o `alg` do ADR-0010.
- Turnos: o estado terminal é *first-wins*; o Laravel aplica só o primeiro `completed`/`failed` e audita o segundo.
- O `cancel.requested` só pára o Python. O estado final (`CANCELLED`, ou `FAILED` para timeout, orçamento e aprovação expirada) é decidido e auditado pelo Laravel (ADR-0013).

## 5. Fora de âmbito
- Testes de produtor e consumidor em PHP e Python (M03 para as mensagens de conversa, M05 para as de missão).
- `POST /v1/retrieval/search` e as mensagens `knowledge.*` (M04).
- Validação semântica completa do AsyncAPI com o parser oficial (só a estrutura e as referências).

## 6. Perguntas abertas
- **[P]** Tamanho máximo da janela de contexto no M03 (100 mensagens é um tecto do contrato, não a política).
- **[H]** Limites de transporte a confirmar no M03: `max_message_size` do RabbitMQ em 16 MiB e corpo HTTP de `tool-authorizations` até 1 MiB (413 acima disso).
