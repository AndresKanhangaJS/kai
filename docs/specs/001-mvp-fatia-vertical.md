# SPEC-001: MVP — fatia vertical fina

- **Estado:** Aprovada
- **Data:** 2026-11-20
- **Milestone:** M01 (spec); implementação faseada em M02–M05
- **Autor:** Claude Code (`kai-spec`), revisão do owner pendente
- **Requisitos:** FR-001–003, FR-008, FR-009, FR-013, FR-021, FR-022, FR-030 (subconjunto), FR-031 (subconjunto), FR-032 (subconjunto), FR-044–062 (subconjunto), FR-066–068 (subconjunto); NFR-001–009, NFR-011–017, NFR-020–021, NFR-026–027
- **ADRs relacionados:** ADR-0013 (substitui ADR-0004: níveis, modo, aprovação, máquina de estados da missão), ADR-0003 (RabbitMQ + Outbox), ADR-0006 (abstracção de LLM), ADR-0007 (baseline de versões), ADR-0008 (object storage — fora de âmbito do MVP), ADR-0010 (autenticação entre serviços)

## 1. Contexto
- **[C D-10]** O MVP é "leitura livre + escrita interna sujeita a aprovação", coerente com o nível 1 da p.13.
- **[C `analysis.md` §6]** A fatia vertical fina cobre: React (login, chat em streaming, aprovação, auditoria); Laravel (Identity, Conversations, Missions, Approvals, Audit, Tool Registry e Policy, Outbox); RabbitMQ; Python (LLM Gateway, Context Builder, Tool Execution com *grants*).
- **[C ADR-0013]** As três decisões que faltavam para tornar os critérios de aceitação verificáveis — máquina de estados da missão (P-003), tabela nível↔modo↔aprovação (P-004) e a lista fechada do nível 6 (P-005) — já estão fechadas.
- **[H]** Esta spec é deliberadamente transversal a vários milestones (M02 Core Foundation, M03 KAI Intelligence, M05 Agent Framework) porque o PDF define o MVP como uma fatia vertical, não um milestone isolado (p.16); cada milestone implementa o subconjunto que lhe compete, mas os critérios de aceitação só se verificam por completo depois do M05.

## 2. Objectivo
Entregar a primeira fatia vertical do KAI — login seguro, conversa em streaming, uma ferramenta de leitura sem aprovação e uma escrita interna com aprovação humana, tudo auditável e com um trace de ponta a ponta — para validar o ciclo completo (Core Platform + AI Engine + mensageria) antes de expandir o produto.

## 3. Critérios de aceitação

| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-01 | Um clone limpo do repositório, com `.env.example` copiado para `.env` | Corro `docker compose up` | Todos os serviços ficam *healthy* em ≤ 10 min (NFR-029) e nenhum segredo está no repositório | integração (infra), secret scan |
| AC-02 | O owner criado por CLI | Faz login com passkey (ou TOTP como alternativa) | Obtém uma sessão válida; uma sessão revogada deixa de autenticar pedidos | integração, E2E |
| AC-03 | O owner autenticado, numa conversa existente | Envia uma mensagem | Os tokens da resposta aparecem incrementalmente (streaming); a mensagem e a resposta persistem depois de recarregar a página | E2E, integração |
| AC-04 | Uma pergunta sobre o repositório GitHub configurado | O KAI invoca `github.repo.read` (nível 1) | A ferramenta corre sem pedido de aprovação; o input e o output são validados por JSON Schema; a resposta cita o resultado | integração, contrato |
| AC-05a | Um pedido do owner para guardar uma nota | O KAI propõe `notes.save` (nível 4) | A missão passa a `AWAITING_APPROVAL`; nada é escrito antes da decisão | integração |
| AC-05b | Uma missão em `AWAITING_APPROVAL` para `notes.save` | O owner rejeita a aprovação | A missão termina em `CANCELLED`; nenhuma escrita acontece | integração, negativo |
| AC-05c | Uma missão em `AWAITING_APPROVAL` para `notes.save` | O owner aprova | A nota é escrita exactamente uma vez (idempotência por passo) | integração |
| AC-06 | Uma ferramenta fora da *allowlist*, ou um *execution grant* ausente/inválido | A execução é tentada, seja qual for o output do LLM | O PEP bloqueia-a; nenhuma chamada ao adaptador acontece (NFR-001) | unit, arquitectura, negativo de segurança |
| AC-07 | Conteúdo de um repositório lido por `github.repo.read` contendo "ignore previous instructions…" | O conteúdo é processado pelo contexto da missão | Não acontece nenhuma chamada de ferramenta extra nem alteração de permissões ou de nível (NFR-005) | eval (suite de prompt injection) |
| AC-08 | Qualquer missão concluída (sucesso, recusa ou cancelamento) | O owner abre a vista de auditoria | Vê actor, agente@versão, ferramenta@versão, modo, nível, decisão e um `trace_id` que abre um único trace React → Laravel → RabbitMQ → Python → LLM (NFR-002, NFR-026) | integração, observabilidade |
| AC-09 | Uma execução em curso | O owner cancela, ou o timeout/orçamento da missão é atingido (NFR-011) | A missão termina em `CANCELLED` ou `FAILED`; a UI mostra o estado *Error* com o motivo | integração, E2E |
| AC-10 | O fornecedor de LLM `fake` (D-08) | A CI corre | Os testes unitários, de contrato e um E2E passam sem rede nem chaves reais (P-015) | CI, contrato |

## 4. Segurança e privacidade

**Níveis de operação (ADR-0013):**
- `github.repo.read` → nível 1, read-only, sem aprovação, só verificação de acesso.
- `notes.save` → nível 4, write, interna e reversível. **[H, D-10]** No MVP exige sempre aprovação explícita, mesmo que a política geral do ADR-0013 permita automatizar o nível 4 quando é interno e reversível — D-10 ("escrita sujeita a aprovação") prevalece enquanto o MVP não tiver avaliação suficiente para confiar na automação. Revisitar depois do M05.
- Nenhuma operação de nível 5 ou 6 entra no MVP; a lista fechada do nível 6 (P-005) não é exercida por nenhuma ferramenta desta spec.
- Uma missão que leu `github.repo.read` sobre conteúdo externo fica *tainted*; isso só tem efeito prático no MVP se `notes.save` for proposta na mesma missão (escalaria para aprovação obrigatória — já é sempre obrigatória por D-10, logo sem efeito observável até ao pós-MVP).

**Dados tocados e isolamento (`user_id` em todas, NFR-009):**
- Identity & Access: `users`, `sessions`.
- Conversations: `conversations`, `messages`.
- Missions: `missions`, `mission_steps`, `mission_events`.
- Approvals: `mission_approvals`.
- Audit: `audit_logs` (append-only).
- Tool Registry & Policy: `tools`, `tool_versions` (sem `user_id`; é configuração global).
- Model Providers & Usage: `model_providers`, `model_usage`.

**Conteúdo não confiável:** o conteúdo do repositório GitHub lido por `github.repo.read` é sempre tratado como não confiável (AC-07); nunca altera a *allowlist*, o nível ou as instruções do agente.

**Ameaças relevantes (resumo; não trivial — recomendo `kai-threat-model` antes da implementação de T4.* em diante):**
- Prompt injection indirecta via conteúdo do repositório (AC-07).
- Replay ou forjadura do *execution grant* — mitigado pelo JWS de uso único, ≤ 60 s, ligado ao hash dos argumentos (ADR-0013, ADR-0010).
- Argumentos alucinados pelo LLM — mitigado por `additionalProperties: false` nos schemas das duas ferramentas.

**Segredos:** nenhum no código, nos prompts ou nos logs; chaves do Anthropic/Ollama só em variáveis de ambiente; a demo e a CI usam o fornecedor `fake` por omissão (P-015), sem chamadas de rede.

## 5. Observabilidade

- **Spans:** `http.server POST /conversations/{id}/messages`, `publish kai.commands`, `llm.generate`, `tool.execute github.repo.read`, `tool.execute notes.save`, `amqp.consume ai.conversation.turn.requested.v1`.
- **Métricas:** `kai_http_server_duration_seconds`, `kai_llm_tokens_total{direction}`, `kai_llm_cost_usd_total`, `kai_tool_executions_total{tool,outcome}`, `kai_mission_outcomes_total{state}`, `kai_queue_dlq_messages`.
- **Logs (sem dados sensíveis):** JSON com `trace_id`, `span_id`, `service`, `level`, `event`; nunca conteúdo de mensagens, prompts ou argumentos de ferramentas — só IDs e hashes.

## 6. Contratos

- **Síncrono (OpenAPI 3.1):** `POST /internal/v1/tool-authorizations` (Python → Laravel); `/health/live`, `/health/ready` (Laravel → Python).
- **Assíncrono (AsyncAPI 3.x + JSON Schema, exchanges `kai.commands`/`kai.events`):** `ai.conversation.turn.requested.v1`, `ai.conversation.turn.completed.v1`/`failed.v1`, `ai.mission.step.reported.v1`, `ai.mission.step.resume.v1`, `ai.mission.cancel.requested.v1`, `ai.model.usage.recorded.v1`.
- Nenhum destes contratos está definido ainda. **A skill `kai-contract` corre antes de qualquer código que os implemente** — esta spec não substitui esse passo.

## 7. Plano de testes

- **Unitários (muitos):** regras de nível/modo/aprovação (ADR-0013), máquina de estados da missão, validação de schema das duas ferramentas.
- **Integração:** MySQL real em contentor; RabbitMQ (Outbox → relay → consumidor); Redis/Reverb (autorização do canal `run.{id}`).
- **Contrato:** exemplos de `tool-authorizations` e das 6 mensagens AsyncAPI, validados dos dois lados.
- **Arquitectura:** teste que prova que nenhum caminho chega a um adaptador de ferramenta sem *grant* válido (NFR-001, cobre AC-06).
- **E2E (poucos, Playwright):** AC-01 a AC-10 directamente.
- **Negativos de segurança explícitos:** sem *grant*; *grant* expirado; argumentos alterados depois da aprovação; `user_id` de outro dono; tentativa de nível 6.
- Todos sem rede nem chaves reais: fornecedor `fake`, fixtures sintéticas (D-08, P-015).

## 8. Fora de âmbito

- Qdrant, pipeline RAG, memória de longo prazo (M04+).
- Object storage / SeaweedFS (M04, ADR-0008).
- Voz: STT, TTS, sessões de voz (M06).
- Núcleo visual 3D (fica um badge de estado simples, FR-007).
- UI completa do Agent Registry; RBAC completo (o MVP só valida por ferramenta, FR-046).
- Registo público de utilizadores (o owner é criado por CLI, D-05).
- Daily Briefing (fora da v1, P-008).
- Editor visual de workflows (P-010).
- Estado `PAUSED` da missão: modelado no ADR-0013, mas nenhum critério desta spec o exercita.
- Pipeline de CI em si (lint, PHPStan, mypy, Pest, Vitest, secret scan): entregue no M02; esta spec consome-o em AC-10, não o define.

## 9. Perguntas abertas

| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-002 | Valores finais dos limites de custo/passos para AC-09 | Usar os valores provisórios ($1/missão, $5/dia) até serem medidos no M03 | Não — a spec usa-os como placeholder |
| P-017 | Passkeys no Laravel 13 (1.ª parte ou pacote) | Spike no M02, antes de implementar AC-02 | Não para a spec; sim para a implementação de AC-02 |
