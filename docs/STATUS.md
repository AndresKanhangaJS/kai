# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** M01 · Product Discovery — Épicos E1 a E4 concluídos; falta só o E5 (identidade visual)
- **Branch:** `chore/claude-harness` (7 commits publicados em `origin/chore/claude-harness`; C4 e correcções da A-12 por commitar)

## Missão de arranque: fases

| Fase | Estado |
|---|---|
| 0 · Orientação | Aprovada |
| 1 · Análise de arquitecto | Aprovada → [`docs/product/analysis.md`](product/analysis.md) |
| 2 · Ambiente de engenharia do Claude Code | Aprovada (2026-11-20) |
| 3 · Verificação do ambiente | **Aprovada (2026-11-20)**. Re-confirmado no WSL: `.claude/hooks/tests/test_guard.sh` → 75 ok/0 falhas; `python3 .claude/scripts/validate_harness.py` → 46 OK/0 avisos/0 erros. Hooks registados no `settings.json`. |
| 4 · Entrega e arranque | **Concluída (2026-11-20).** 5 commits aprovados pelo owner, criados e publicados em `origin/chore/claude-harness` (sem PR/merge ainda). |

## Notas de ambiente

- A Fase 2 foi feita numa sessão Windows, sobre `\\wsl.localhost`; os hooks e o validador foram testados no WSL através de `wsl.exe`.
- Os hooks estão registados no `.claude/settings.json` desde o fim da Fase 3. A partir daqui, o Claude Code só deve correr **dentro do WSL**, porque os hooks precisam de `bash` + `python3`.
- No WSL, a versão instalada do Claude Code é a 2.1.211. A `stable` no npm é a 2.1.311 (verificada a 2026-11-20); convém actualizar.
- `poppler-utils` instalado no WSL a 2026-11-20 (autorizado pelo owner, correu fora do guard por usar `sudo`), para ler visualmente as páginas do PDF de produto. Utilitário de sistema, não é dependência do projecto.
- Não criar nesta missão:
  - `LICENSE` (Apache-2.0 já decidida, D-02);
  - CI;
  - `apps/`, `services/`, `packages/`, `infrastructure/`;
  - `docker-compose.yml`.

## Decisões recentes

- D-01 a D-18: ver [`analysis.md` §0](product/analysis.md#0-decisões-do-owner-passam-a-c).
- ADRs: ver [`docs/adr/`](adr/README.md). **12 aceites** (0000, 0001, 0002, 0003, 0005, 0006, 0007, 0008, 0009, 0010, 0011, 0012), **1 substituído** (0004 → ADR-0013), **1 novo aceite** (0013). Todos os ADRs do M01 estão decididos.
- **ADR-0013** (substitui o ADR-0004): modelo de segurança completo — PEP-1/PEP-2 e *execution grants*; tabela nível↔modo↔aprovação (P-004); lista fechada do nível 6 (P-005); máquina de estados da missão com 8 estados (P-003).
- **ADR-0009** aceite com uma condição explícita: depende de um spike no M03 que confirme a publicação HTTP no Reverb; se falhar, cai para o fallback SSE já documentado no próprio ADR.
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado.

## M01 · Product Discovery

Decomposto em 5 épicos (E1–E5) e 16 tarefas → [`docs/milestones/M01-product-discovery.md`](milestones/M01-product-discovery.md).

**Feito (2026-11-20):** Épico E1 (ADRs), E2 (P-006, P-008), E3 (spec + PRD), e agora **E4** — [C4 nível 1](architecture/c4-01-context.md) e [nível 2](architecture/c4-02-containers.md), mais a correcção da A-12: o diagrama da p.7 do PDF não tinha as caixas MESSAGING/PERSISTENCE vazias (erro da extracção de texto); a Observability aparece como coluna à parte, ligada à fronteira Core Platform/AI Intelligence.

**Falta:** só o **Épico E5** — identidade visual mínima dark-first (T5.1, T5.2).

## Próximas 3 tarefas

1. Épico E5, T5.1: nome visual, paleta dark-first e tipografia mínima, acessíveis (WCAG 2.2 AA).
2. Épico E5, T5.2: registar a identidade visual em `docs/product/`, ligada do README e do PRD.
3. Depois do E5: M01 fica concluído — rever a verificação do milestone e fazer o relatório final de fecho.

## Perguntas abertas

- P-003 a P-006, P-008: **fechadas (2026-11-20)** → [ADR-0013](adr/0013-modelo-de-seguranca.md) e [`prd.md` §3](product/prd.md#3-âmbito-do-mvp-fatia-vertical-fina). As restantes, P-001, P-002, P-007, P-009 a P-017: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M01.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação no M02: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
