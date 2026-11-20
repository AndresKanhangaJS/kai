# PRD — KAI (MVP)

- **Estado:** Aprovado (2026-11-20)
- **Data:** 2026-11-20
- **Milestone:** M01 (Product Discovery)
- **Fontes:** [C] PDF p.4–5, p.16–19; `docs/product/analysis.md`; `docs/specs/001-mvp-fatia-vertical.md`; ADR-0013

## 1. Visão e problema

**Declaração de visão [C p.4]:** "Criar uma inteligência pessoal que compreenda o contexto do utilizador e execute operações autorizadas, mantendo-o sempre informado e no controlo."

**Problemas que o KAI quer resolver [C p.4]:**
- Fragmentação do trabalho entre várias aplicações e serviços.
- Repetição de tarefas manuais e fluxos operacionais.
- Dificuldade em recuperar contexto disperso em conversas e documentos.
- Falta de uma interface única para consultar e coordenar ferramentas autorizadas.

**Duplo propósito [C p.2]:** o KAI é, ao mesmo tempo, um produto útil no dia-a-dia e um laboratório público de engenharia de software, AI engineering, segurança e observabilidade.

## 2. Persona

**[H]** Uma só persona no MVP: o **owner**, utilizador individual e engenheiro de software, que é simultaneamente o utilizador final e quem opera e audita o sistema. A evolução para multi-utilizador está preparada mas fora do MVP (D-05, `analysis.md` A-14).

## 3. Âmbito do MVP: fatia vertical fina

**[C `analysis.md` §6]** O MVP corta na vertical, não por módulo: login, conversa em streaming, uma ferramenta de leitura sem aprovação, uma ferramenta de escrita interna com aprovação humana, auditoria e um trace de ponta a ponta. Os critérios de aceitação completos (AC-01 a AC-10) e os detalhes de segurança, contratos e testes estão em `docs/specs/001-mvp-fatia-vertical.md` (SPEC-001) — este PRD não os repete, só os enquadra em casos de uso.

**Cenário de demonstração [C P-008]:** o Daily Briefing (que precisaria de email e calendário, fora da v1) não é o cenário de arranque; o primeiro cenário demonstrável é o **Developer Assistant** — o owner faz uma pergunta sobre um repositório GitHub configurado e o KAI responde com `github.repo.read`.

**Idioma (P-006):** a conversa funciona em português e em inglês (FR-010); a interface arranca em português, preparada para internacionalização mais tarde — não há UI bilingue no MVP.

## 4. Casos de uso do MVP

| ID | Caso de uso | Critério(s) de aceitação |
|---|---|---|
| UC-01 | O owner arranca o ambiente local com um comando, sem segredos no repositório | AC-01 |
| UC-02 | O owner autentica-se com passkey (ou TOTP) e pode revogar uma sessão | AC-02 |
| UC-03 | O owner conversa com o KAI e vê a resposta aparecer em streaming, persistida ao recarregar | AC-03 |
| UC-04 | O owner pergunta sobre o repositório configurado (Developer Assistant); o KAI lê-o e cita a resposta, sem pedir aprovação (nível 1) | AC-04 |
| UC-05 | O owner pede para guardar uma nota; o KAI propõe a escrita, que fica pendente até o owner aprovar ou rejeitar | AC-05a, AC-05b, AC-05c |
| UC-06 | Uma tentativa de usar uma ferramenta fora da *allowlist*, ou sem autorização válida, é bloqueada antes de chegar a qualquer adaptador | AC-06 |
| UC-07 | Um repositório com instruções escondidas ("ignora as instruções anteriores…") não consegue alterar o comportamento do KAI nem as suas permissões | AC-07 |
| UC-08 | O owner audita qualquer missão concluída e segue o trace completo, da interface ao LLM | AC-08 |
| UC-09 | O owner cancela uma execução em curso, ou esta termina por exceder o tempo/orçamento, sempre com um motivo visível | AC-09 |
| UC-10 | Quem clona o repositório corre a suite de testes sem chaves nem rede, usando o fornecedor `fake` | AC-10 |

## 5. Fora de âmbito do MVP

**[C `analysis.md` §6, SPEC-001 §8]** Qdrant e RAG; object storage; voz (STT/TTS); núcleo visual 3D (fica um badge de estado); UI completa do Agent Registry; RBAC completo (só por ferramenta); registo público (o owner é criado por CLI); Daily Briefing (P-008); editor visual de workflows (P-010); estado `PAUSED` da missão (modelado, não exercitado).

## 6. Métricas de sucesso

**[C p.19, metas H confirmadas em `analysis.md` §3.2]**

| Métrica | Meta |
|---|---|
| Task Success Rate (NFR-020) | ≥ 80%, regressão > 3 pp bloqueia a release |
| Tool Success Rate (NFR-021) | ≥ 95%, sem contar recusas de política |
| Groundedness (NFR-018) | ≥ 0,90, 100% das respostas com fonte |
| Tempo até ao 1.º token (NFR-015) | p50 ≤ 1,5 s · p95 ≤ 3 s |
| Latência Q&A (NFR-016) | p95 ≤ 8 s |
| Cost per Task | Medido a partir do M03 (D-14, P-002); sem meta fixa no MVP |

Medidas com avaliações versionadas (`kai-eval`), nunca por impressão subjectiva de demo (regra de testes, PDF p.19).

## 7. Riscos principais

**[C `analysis.md` §4.3]**, só os que afectam directamente o MVP:
- **Scope creep** (A/A): os 10 casos de uso acima são o tecto; qualquer pedido fora deles vai para "Depois" sem discussão.
- **Prompt injection indirecta** (A/A): mitigada por UC-07 / AC-07 e pela regra de que o conteúdo externo nunca altera permissões.
- **Custo descontrolado** (M/A): sem meta fixa ainda (P-002); usa-se um tecto provisório até ser medido no M03.
- **Projecto de uma pessoa que estagna** (M/A): o MVP está cortado em casos de uso pequenos e demonstráveis um a um.

## 8. Fora deste documento

- C4 de nível 1–2 e a confirmação visual dos bounded contexts: [`docs/architecture/c4-01-context.md`](../architecture/c4-01-context.md) e [`c4-02-containers.md`](../architecture/c4-02-containers.md) (Épico E4, feito).
- Identidade visual mínima: [`docs/product/identidade-visual.md`](identidade-visual.md) (Épico E5).
- Os ADRs do M01 (0000, 0001, 0002, 0005, 0009, 0013): todos `Aceite` — ver [`docs/adr/README.md`](../adr/README.md) (Épico E1, feito).
- Requisitos funcionais e não funcionais completos, com a etiqueta [C]/[H]/[P] e a página de origem: `docs/product/analysis.md` §3.

## 9. Aprovação

**Aprovado pelo owner a 2026-11-20.**
