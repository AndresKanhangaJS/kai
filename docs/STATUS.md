# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** M01 · Product Discovery — caminho crítico concluído; falta o resto do E1, E4 e E5
- **Branch:** `chore/claude-harness` (6 commits publicados em `origin/chore/claude-harness`; spec+PRD por commitar)

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
- Não criar nesta missão:
  - `LICENSE` (Apache-2.0 já decidida, D-02);
  - CI;
  - `apps/`, `services/`, `packages/`, `infrastructure/`;
  - `docker-compose.yml`.

## Decisões recentes

- D-01 a D-18: ver [`analysis.md` §0](product/analysis.md#0-decisões-do-owner-passam-a-c).
- ADRs: ver [`docs/adr/`](adr/README.md). 8 aceites (0003, 0006, 0007, 0008, 0010, 0011, 0012, 0013), 1 substituído (0004 → ADR-0013), 4 propostos para revisão no M01 (0000, 0001, 0002, 0005, 0009).
- **ADR-0013** (substitui o ADR-0004): modelo de segurança completo — PEP-1/PEP-2 e *execution grants*; tabela nível↔modo↔aprovação (P-004); lista fechada do nível 6 (P-005); máquina de estados da missão com 8 estados (P-003).
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado.

## M01 · Product Discovery

Decomposto em 5 épicos (E1–E5) e 16 tarefas → [`docs/milestones/M01-product-discovery.md`](milestones/M01-product-discovery.md).

**Caminho crítico concluído (2026-11-20):** ADR-0013 (P-003/004/005) → [`docs/specs/001-mvp-fatia-vertical.md`](specs/001-mvp-fatia-vertical.md) (Aprovada) → [`docs/product/prd.md`](product/prd.md) (Aprovado). Falta: Épico E1 restante, E4 (C4) e E5 (identidade visual) — todos paralelizáveis entre si.

## Próximas 3 tarefas

1. Épico E1 restante: ADR-0000, ADR-0001, ADR-0002, ADR-0005, ADR-0009 (sem dependências entre si, podem correr em qualquer ordem).
2. Épico E4: C4 nível 1–2 (`kai-c4`), depois do ADR-0002.
3. Épico E5: identidade visual mínima dark-first.

## Perguntas abertas

- P-003, P-004, P-005, P-006, P-008: **fechadas (2026-11-20)** → [ADR-0013](adr/0013-modelo-de-seguranca.md) e [`prd.md` §3](product/prd.md#3-âmbito-do-mvp-fatia-vertical-fina). As restantes, P-001, P-002, P-007, P-009 a P-017: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M01.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação no M02: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
