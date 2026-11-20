# Estado do projecto KAI

- **Actualizado:** 2026-11-20
- **Milestone actual:** M02 · Core Foundation — **Épico E1 concluído**; E4.1–E4.3 feitas; E2, E3, resto de E4 por fazer
- **Branch:** `chore/claude-harness` (1 commit local ainda por publicar; migração de Identity & Access por commitar)

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
- **Bug encontrado e corrigido na E1.4:** `php artisan serve` só reenvia ao processo que serve os pedidos as variáveis de ambiente que já existem no ficheiro `.env`, nunca as que só estão no Docker Compose. Um `.env`/`database.sqlite` residual do scaffold original mascarou isto na E1.2 (parecia "healthy", mas servia pedidos via SQLite, não MySQL). A E1.4, com um `git clone` real para `/tmp`, expôs o problema; corrigido a invocar `php -S` directamente no `apps/api/Dockerfile`. Re-confirmado nos dois sítios.
- Resíduo a limpar (não é crítico): `/tmp/kai-ac01-test`, o clone de teste da E1.4. O `rm -rf` para fora dos caminhos seguros do repositório é bloqueado pelo guard de propósito; o owner pode apagá-lo manualmente quando quiser.

## Decisões recentes

- D-01 a D-18: ver [`analysis.md` §0](product/analysis.md#0-decisões-do-owner-passam-a-c).
- ADRs: ver [`docs/adr/`](adr/README.md). 12 aceites, 1 substituído (0004 → 0013). Todos os ADRs do M01 estão decididos; nenhum novo ADR aberto ainda para o M02.
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado (instalação pede aprovação no M02, D-18).

## M02 · Core Foundation

Decomposto em 4 épicos e 17 tarefas → [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md).

- **E1 (concluído):** monorepo mínimo (`apps/api`, `apps/web`, `packages/contracts`) e Docker Compose; AC-01 verificada a partir de um clone limpo; fecha P-015 (fornecedor `fake` por omissão).
- **E2:** CI — lint, PHPStan, mypy, Pest, Vitest, validação de schemas, secret scan.
- **E3:** contratos v1 (`kai-contract`) — síncrono (`tool-authorizations`, health) e os 6 schemas assíncronos do MVP, antes de o RabbitMQ existir (chega no M03).
- **E4 (E4.1–E4.3 feitas):** Identity & Access — login passkey/TOTP, revogação de sessão. P-017 fechada: `laravel/fortify` + `laravel/passkeys` instalados. Spec aprovada: [`docs/specs/002-identity-access.md`](specs/002-identity-access.md) (7 critérios). Modelo de ameaças: [`docs/security/threat-model-identity-access.md`](security/threat-model-identity-access.md) (11 ameaças STRIDE). Migração: `user_preferences` nova e `sessions` com `last_authenticated_at` + FK a `users`; `migrate → rollback → migrate` verificado contra MySQL real; 4 testes PHPUnit novos (6/6 a passar).

**Critério de aceitação:** AC-01 e AC-02; CI verde.

**Caminho crítico:** ~~E1.1 → E4.1 → E4.2 → E4.3~~ → E4.5 (login) → E4.6 (E2E, AC-02). E1 (AC-01) já está feito.

## Próximas 3 tarefas

1. E4.4: comando `artisan` para criar o owner por CLI (sem registo público, D-05) — paralelo com E4.5.
2. E4.5: implementa login (passkey/TOTP), aplicando as mitigações do modelo de ameaças (T-04 *throttle*, T-06 cifra confirmada) — caminho crítico.
3. E3.1/E3.2: definir os contratos v1 com `kai-contract`, em paralelo.

## Perguntas abertas

- P-015, P-017: **fechadas (2026-11-20)** → [`.env.example`](../.env.example) e [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md) (E4.1).
- Restantes P-xxx: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M02.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação explícita no M02, ainda não pedida: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
