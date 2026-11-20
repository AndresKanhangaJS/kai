# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** M01 · Product Discovery, caminho crítico iniciado (P-003/004/005 fechadas)
- **Branch:** `chore/claude-harness` (5 commits publicados em `origin/chore/claude-harness`; ADRs do M01 por commitar)

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

Caminho crítico: ~~ADR-0013 (P-003, P-004, P-005)~~ **feito (2026-11-20)** → spec do MVP (`kai-spec`, T3.1) → PRD → aprovação do owner. Em paralelo: restantes ADRs (E1), P-006/P-008 (E2), identidade visual (E5), e o C4 (E4) depois do ADR-0002.

## Próximas 3 tarefas

1. Spec do MVP com `kai-spec` (T3.1), a partir de AC-01 a AC-10 — já pode arrancar, P-003/004/005 estão fechadas.
2. Em paralelo: Épico E1 restante — ADR-0000, ADR-0001, ADR-0002, ADR-0005, ADR-0009.
3. Em paralelo: P-006 e P-008 (Épico E2) e a identidade visual mínima (Épico E5).

## Perguntas abertas

- P-003, P-004, P-005: **fechadas (2026-11-20)** → [ADR-0013](adr/0013-modelo-de-seguranca.md). P-006, P-008: recomendação escrita em `analysis.md`, ainda a ratificar no M01. As restantes, P-001, P-002, P-007, P-009 a P-017: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M01.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação no M02: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
