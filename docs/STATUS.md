# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** pré-M01, missão de arranque do harness de engenharia
- **Branch:** `chore/claude-harness` (72 ficheiros por commitar; commits agrupados propostos na Fase 4, a aguardar aprovação do owner)

## Missão de arranque: fases

| Fase | Estado |
|---|---|
| 0 · Orientação | Aprovada |
| 1 · Análise de arquitecto | Aprovada → [`docs/product/analysis.md`](product/analysis.md) |
| 2 · Ambiente de engenharia do Claude Code | Aprovada (2026-11-20) |
| 3 · Verificação do ambiente | **Aprovada (2026-11-20)**. Re-confirmado no WSL: `.claude/hooks/tests/test_guard.sh` → 75 ok/0 falhas; `python3 .claude/scripts/validate_harness.py` → 46 OK/0 avisos/0 erros. Hooks registados no `settings.json`. |
| 4 · Entrega e arranque | **Em curso.** Commits agrupados propostos (ver secção abaixo), a aguardar aprovação do owner para `git commit`. |

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
- ADRs 0000 a 0012: ver [`docs/adr/`](adr/README.md). Seis estão aceites; os restantes estão propostos para revisão no M01.
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado.

## Próximas 3 tarefas

1. Owner: aprovar (ou pedir ajustes a) os 5 commits agrupados propostos na Fase 4; só depois há `git commit` (sem push sem confirmação explícita).
2. Arrancar a sessão 1 do M01 (Product Discovery) com a skill `kai-milestone`, decompondo o milestone em épicos e tarefas.
3. M01: fechar P-003, P-004, P-005, P-006 e P-008, e rever os ADRs propostos.

## Perguntas abertas

- P-001 a P-017: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes). Nenhuma bloqueia as Fases 3 e 4.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação no M02: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
