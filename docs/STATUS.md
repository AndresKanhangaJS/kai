# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** M02 · Core Foundation — Épico E1 em curso (E1.1 feita)
- **Branch:** `chore/claude-harness` (8 commits publicados em `origin/chore/claude-harness`; apps/api, apps/web, packages/contracts por commitar)

## Milestones concluídos

| Milestone | Estado |
|---|---|
| Missão de arranque do harness (Fases 0–4) | **Concluída (2026-11-20).** Harness do Claude Code, hooks, skills, agentes e regras publicados em `chore/claude-harness`. Ver histórico abaixo. |
| M01 · Product Discovery | **Concluído (2026-11-20).** PRD e ADRs aprovados; P-003 a P-006 e P-008 fechados; C4 nível 1–2; identidade visual mínima. Ver [`docs/milestones/M01-product-discovery.md`](milestones/M01-product-discovery.md). |

## Notas de ambiente

- O Claude Code corre **dentro do WSL** (hooks precisam de `bash` + `python3`); os hooks estão registados em `.claude/settings.json`.
- No WSL, a versão instalada do Claude Code é a 2.1.211. A `stable` no npm é a 2.1.311 (verificada a 2026-11-20); convém actualizar.
- `poppler-utils` instalado no WSL a 2026-11-20 (autorizado pelo owner, correu fora do guard por usar `sudo`), para ler visualmente páginas do PDF de produto. Utilitário de sistema, não é dependência do projecto.
- A restrição "não criar `apps/`, `CI`, `docker-compose.yml`" aplicava-se só à missão de arranque do harness (concluída). O M02 é o milestone que os introduz deliberadamente — ver decomposição abaixo.
- `LICENSE` (Apache-2.0, D-02) continua por criar; entra antes da primeira publicação de código, não necessariamente no M02.
- Toolchain local confirmado 2026-11-20: Node v20.20.2, npm 10.8.2, Docker 29.4.3 presentes; **PHP e Composer não estão instalados localmente**. `apps/api` foi criado via Docker (imagem `php:8.5-cli` + binário `composer` extraído de `composer:latest`), sem instalar nada no sistema. Decisão do owner: scaffold via Docker, não instalação local.
- O scaffold do Laravel gera `apps/api/CLAUDE.md` e `AGENTS.md` com instruções do "Laravel Boost" para qualquer agente instalar PHP via `curl | bash` e o pacote `laravel/boost` automaticamente. Tratado como conteúdo não confiável (regra de segurança 4) e substituído por um apontador às regras do KAI — Boost continua por decidir (D-18), nunca auto-instalado.
- `.claude/scripts/validate_harness.py` actualizado: a lista de pastas proibidas já não inclui `apps`/`packages`/`docker-compose.yml` (o M02 introduz-os deliberadamente); passou a excluir `vendor/`, `node_modules/`, `dist/`, `build/` da verificação de links e do scan de segredos (eram falsos positivos de dependências de terceiros).

## Decisões recentes

- D-01 a D-18: ver [`analysis.md` §0](product/analysis.md#0-decisões-do-owner-passam-a-c).
- ADRs: ver [`docs/adr/`](adr/README.md). 12 aceites, 1 substituído (0004 → 0013). Todos os ADRs do M01 estão decididos; nenhum novo ADR aberto ainda para o M02 (pode surgir do spike de passkeys, E4.1).
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado (instalação pede aprovação no M02, D-18).

## M02 · Core Foundation

Decomposto em 4 épicos e 17 tarefas → [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md).

- **E1:** monorepo mínimo (`apps/api`, `apps/web`, `packages/contracts`) e Docker Compose; fecha P-015 (fornecedor `fake` por omissão).
- **E2:** CI — lint, PHPStan, mypy, Pest, Vitest, validação de schemas, secret scan.
- **E3:** contratos v1 (`kai-contract`) — síncrono (`tool-authorizations`, health) e os 6 schemas assíncronos do MVP, antes de o RabbitMQ existir (chega no M03).
- **E4:** Identity & Access — login passkey/TOTP, revogação de sessão; fecha P-017 (spike de passkeys no Laravel 13).

**Critério de aceitação:** AC-01 e AC-02; CI verde.

**Caminho crítico:** E1.1 → E4.1 (spike passkeys) → E4.2 (spec) → E4.3 (migração) → E4.5 (login) → E4.6 (E2E, AC-02). Em paralelo: E1.2–E1.4 (AC-01), E2.1/E2.2/E2.4, E3.1–E3.3 → E2.3.

**Risco a vigiar:** se o spike de passkeys (E4.1) exigir um pacote novo, isso é uma dependência nova — pára e pede aprovação antes de a adicionar (regra de ouro de segurança).

## Próximas 3 tarefas

1. E1.2: `docker-compose.yml` com `api`, `web`, MySQL 8.4, Redis 8 e *health checks*.
2. E4.1: spike de passkeys no Laravel 13 (fecha P-017) — pode correr em paralelo com E1.
3. E3.1/E3.2: definir os contratos v1 com `kai-contract`, em paralelo com o resto.

## Perguntas abertas

- P-015, P-017: a fechar no M02 (E1.3 e E4.1, respectivamente) — ver [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md).
- Restantes P-xxx: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M02.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação explícita no M02, ainda não pedida: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
