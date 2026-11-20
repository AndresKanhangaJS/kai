# M01: Product Discovery

**Objectivo:** fechar o discovery de produto do KAI — PRD aprovado, FR/NFR confirmados, C4 de nível 1–2, bounded contexts claros, os ADRs 0000–0012 revistos e decididos, e uma identidade visual mínima — para o M02 (Core Foundation) arrancar sobre uma base estável.

**Critério de aceitação (PDF p.18 / `analysis.md` §7):** PRD e ADRs aprovados; P-003, P-004, P-005, P-006 e P-008 fechados.

**Dependências:** esta análise (`docs/product/analysis.md`, aprovada pelo owner a 2026-11-20); harness de engenharia (Fases 0–4, concluídas).

**P-xxx resolvidas neste milestone:** P-003 (transições da missão), P-004 (nível↔modo↔aprovação), P-005 (lista do nível 6), P-006 (âmbito PT/EN), P-008 (Daily Briefing).

**Nota sobre pré-condições:** as cinco P-xxx acima já têm uma recomendação escrita em `analysis.md` (§5.3, §5.4, §4.2), mas nenhuma foi ainda ratificada pelo owner — ratificá-las é precisamente o trabalho do Épico E1/E2, não uma pré-condição para o decompor. Nenhuma outra dependência deste milestone está pendente.

---

## Épico E1: ADRs 0000–0012 revistos e decididos, incluindo P-003/P-004/P-005 (FR-060, FR-061, FR-062, NFR-001, NFR-002, NFR-003, NFR-004; ADR-0000, ADR-0002, ADR-0005, ADR-0009, ADR-0013)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| T1.1 | Revê e decide o ADR-0000 (registar decisões arquitecturais, MADR) | docs (`kai-adr`) | ADR-0000 passa a "Aceite"; índice `docs/adr/README.md` actualizado | — | Sim |
| T1.2 | Revê e decide o ADR-0001 (modular monolith Laravel + AI Engine Python) | docs (`kai-adr`) | ADR-0001 "Aceite"; resolve A-02 (KAI Core vs Core Platform) | — | Sim |
| T1.3 | ~~Decide P-003 (transições da missão, §5.3) e integra a máquina de estados no ADR-0004~~ | docs (`kai-adr`) | **Feito (2026-11-20).** Decisão carregada para o ADR-0013 (substituiu o ADR-0004); `analysis.md` §4.2 marca P-003 "Fechado" | — | Não (mesmo ADR que T1.4) |
| T1.4 | ~~Decide P-004 (nível↔modo↔aprovação, §5.4) e P-005 (lista do nível 6)~~ | docs (`kai-adr`) | **Feito (2026-11-20).** ADR-0013 "Aceite" com as três decisões (P-003, P-004, P-005); ADR-0004 "Substituído por ADR-0013"; `analysis.md` §4.2 marca P-004 e P-005 "Fechado" | T1.3 | Não |
| T1.5 | Revê e decide o ADR-0002 (fronteira de contratos Laravel ↔ Python), resolvendo A-03 | docs (`kai-adr`) | ADR-0002 "Aceite" | — | Sim |
| T1.6 | Revê e decide o ADR-0005 (memória e RAG: MySQL, Qdrant, S3) | docs (`kai-adr`) | ADR-0005 "Aceite"; regista P-014 como aberta para o M04 | — | Sim |
| T1.7 | Revê e decide o ADR-0009 (streaming de tokens por Reverb), marcando o spike do M03 | docs (`kai-adr`) | ADR-0009 "Aceite" com a condição do spike e o fallback SSE documentados | — | Sim |

## Épico E2: decisões de produto fechadas — P-006 e P-008 (FR-010; sem ADR novo)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| T2.1 | ~~Decide P-006~~ | docs | **Feito (2026-11-20).** `analysis.md` §4.2 marca P-006 "Fechado"; registado em `prd.md` §3 | — | Sim |
| T2.2 | ~~Decide P-008~~ | docs | **Feito (2026-11-20).** `analysis.md` §4.2 marca P-008 "Fechado"; registado em `prd.md` §3 (cenário Developer Assistant) | — | Sim |

## Épico E3: PRD e casos de uso do MVP (FR-001–003, FR-008, FR-009, FR-013, FR-021, FR-022, FR-044–062 subconjunto MVP; NFR-015, NFR-016, NFR-020, NFR-021)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| T3.1 | ~~Escreve a spec do MVP com `kai-spec`~~ | spec (`kai-spec`) | **Feito (2026-11-20).** `docs/specs/001-mvp-fatia-vertical.md`, estado "Aprovada", cobre AC-01 a AC-10 (AC-05 dividido em a/b/c) | T1.3, T1.4 | Não |
| T3.2 | ~~Escreve o PRD~~ | docs | **Feito (2026-11-20).** `docs/product/prd.md`, estado "Rascunho", com visão, persona, 10 casos de uso ligados às AC, fora de âmbito e riscos | T3.1, T2.1, T2.2 | Não |
| T3.3 | ~~Owner aprova o PRD~~ | aprovação | **Feito (2026-11-20).** `prd.md` marcado "Aprovado (2026-11-20)" | T3.2 | Não |

## Épico E4: C4 nível 1–2 e bounded contexts (NFR-001, NFR-026; ADR-0001, ADR-0002, ADR-0003, ADR-0010)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| T4.1 | Diagrama C4 nível 1 (contexto) com `kai-c4` | docs (`kai-c4`) | Diagrama Mermaid em `docs/architecture/`, owner + KAI + integrações externas (GitHub) | T1.5 | Não |
| T4.2 | Diagrama C4 nível 2 (contentores: React, Laravel, Python, RabbitMQ, MySQL, Redis; Qdrant e SeaweedFS marcados "planeado, M04") com `kai-c4` | docs (`kai-c4`) | Diagrama Mermaid coerente com §5.1 da análise | T4.1 | Não |
| T4.3 | Confirma visualmente os bounded contexts de §5.1 contra o diagrama da p.7 do PDF (resolve A-12) | revisão (`kai-architect`) | A-12 marcado "Resolvido" em `analysis.md` §4.1, com nota sobre MESSAGING/PERSISTENCE/Observability | T4.2 | Não |

## Épico E5: identidade visual mínima (FR-066, FR-068)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| T5.1 | Define nome visual, paleta dark-first e tipografia mínima (FR-066), e um esquema simples para os estados do núcleo que entram no MVP (FR-068, sem Listening/Speaking) | design/docs | Paleta e tipografia documentadas, acessíveis (contraste WCAG 2.2 AA, NFR-030) | — | Sim |
| T5.2 | Regista a identidade visual em `docs/product/` | docs | Documento ligado do README e do PRD | T5.1 | Não |

---

## Ordem e caminho crítico

1. **Caminho crítico:** T1.3 → T1.4 → T3.1 → T3.2 → T3.3. **Concluído (2026-11-20).** (A máquina de estados e os níveis/modos tinham de estar decididos antes da spec do MVP, porque definem AC-05, AC-06 e AC-09.)
2. **Em paralelo com o caminho crítico:** T1.1, T1.2, T1.5, T1.6, T1.7, T2.1, T2.2, T5.1 → T5.2.
3. **Depois de T1.5 (ADR-0002 decidido):** T4.1 → T4.2 → T4.3, em paralelo com T3.*.
4. T3.3 (aprovação do PRD) é o último gate antes de fechar o milestone.

## Riscos

| Risco | P/I | Mitigação |
|---|---|---|
| Decidir P-003/P-004/P-005 revela uma lacuna de arquitectura não prevista | M/M | Registar uma P-xxx nova em vez de a resolver às pressas dentro do ADR; liga-se a "Infraestrutura antes de valor" (`analysis.md` §4.3) |
| PRD cresce além do MVP congelado | A/A | Scope creep (`analysis.md` §4.3): os critérios AC-01 a AC-10 de §6 são o tecto; qualquer FR fora disso vai para "Depois" sem discussão |
| Milestone de uma só pessoa estagna à espera de decisões do owner | M/A | Projecto de uma pessoa que estagna (`analysis.md` §4.3): tarefas pequenas e sequenciadas (T1.1–T1.7 paralelizáveis) para haver sempre algo aprovável |
| ADRs "Aceites" ficam desalinhados com o PRD escrito depois (T3.2) | B/M | T3.2 depende explicitamente de T2.1/T2.2 e referencia os ADRs já decididos em E1, nunca o inverso |

## Verificação do milestone

- Todos os ADRs 0000–0012 em `docs/adr/` com estado "Aceite" (os já aceites mantêm-se; os 6 propostos passam a decididos).
- `docs/product/analysis.md` §4.2: P-003, P-004, P-005, P-006, P-008 marcados "Fechado", cada um com link para o ADR ou secção do PRD que o decide.
- PRD em `docs/product/` com estado "Aprovado" e data.
- Diagramas C4 nível 1 e 2 em `docs/architecture/`, Mermaid, renderizáveis.
- Identidade visual mínima documentada e ligada do README.
- `docs/STATUS.md` actualizado a reflectir o M01 fechado e a abertura do M02.

## Estimativa

Não incluída (PDF p.18: "sem estimativas de duração"). Se quiseres uma estimativa por tarefa, pede-a explicitamente depois desta decomposição.
