# Estado do projecto KAI

- **Actualizado:** 2026-11-24 (M03 E1, E2.1, E2.2, E3.1, E3.2, E3.3, E3.4a e E5.0)
- **Milestone actual:** M02 · Core Foundation — **Épicos E1 e E4 concluídos**; **E1–E4 concluídos; CI verde no GitHub** (corrida 45156786354, 5/5 jobs, 2026-11-23). Para fechar o M02 falta o owner activar o secret scanning (E2.4), aprovar o ADR-0014 e fazer merge do PR. **M03 decomposto** ([`M03-kai-intelligence.md`](milestones/M03-kai-intelligence.md))
- **Branch:** `chore/m02-ci` (E2 e E3; PR aberto para `main`, CI verde). M03 em `feat/m03-reverb-spike` (até à E3.4a); protótipo do chat em `feat/m03-chat-prototype` (por cima da anterior)

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
- **Bug encontrado e corrigido na E4.4:** os testes PHPUnit corriam silenciosamente contra o **MySQL real** do Docker Compose, não o SQLite em memória que `apps/api/phpunit.xml` tenta forçar. Causa: o Docker Compose define `DB_CONNECTION`/`DB_DATABASE`/`APP_ENV` como variáveis de ambiente reais do contentor, que populam `$_ENV`/`$_SERVER` antes do PHPUnit arrancar; o `env()` do Laravel lê esses primeiro, e o `<env force="true">` do PHPUnit só corrige `getenv()`, não `$_ENV`. Confirmado empiricamente: a tabela `migrations` do MySQL real aparecia cheia depois de uma simples corrida de testes. **Resolvido na E2:** usa `scripts/ci/api.sh`; além disso, o `tests/TestCase.php` recusa correr fora do SQLite em memória (guarda testada em `TestDatabaseIsolationTest`).
- **Bug grave encontrado e corrigido na E4.5 (invalidava verificações anteriores):** depois de trocar `php artisan serve` por `php -S` (E1.4), **todos os pedidos HTTP ao `api`, incluindo `/`, davam erro fatal do PHP** (o *router* do Laravel resolve `public/index.php` a partir de `getcwd()`, não do `-t public`; com `WORKDIR /app`, tentava abrir `/app/index.php`, que não existe). O erro vinha com HTTP 200 (PHP com `display_errors` devolve HTML de erro, não 500), por isso o healthcheck (só verificava "houve resposta") e os `curl` anteriores nunca o apanharam. Corrigido: o `CMD` muda para `public/` antes de invocar `php -S` (como o `artisan serve` já fazia internamente). Healthcheck do `api` reforçado para confirmar que a resposta não é uma página de erro. Reconfirmado com um pedido real de ponta a ponta (CSRF → login TOTP → listar sessões) contra o MySQL real.
- **Bug encontrado pelo owner na E4.6a, só visível num browser real:** `config/cors.php` tinha `'login'` nos `paths`, que só cobre a rota exacta `/login`, não `/login/totp` — o `curl` não detecta isto (CORS é imposto pelo browser). O *preflight* falhava silenciosamente, dando "Falha inesperada" na UI. Corrigido (`'login/*'`); confirmado com um `OPTIONS` real e depois um login completo no Chrome do owner.

- **E4.6b, ambiente:** o Docker é o Docker Desktop (WSL), onde `network_mode: host` não chega às portas publicadas. O contentor E2E fica na rede da stack e usa `apps/web/e2e/port-forward.mjs` para `localhost:5173/8000` apontarem para `web`/`api` (a origem WebAuthn tem de ser `http://localhost:5173`). A stack `kai-e2e` usa as mesmas portas da de dev (5173, 8000, 3306): `scripts/e2e.sh` recusa correr se estiverem ocupadas. Partilha com a de dev o bind mount de `apps/api` (ficheiro de ambiente e `APP_KEY`), mas os logs vão para o stderr do contentor (`docker-compose.e2e.yml`), não para o `laravel.log`. Desde a E4.6b, as portas de dev publicam só em `127.0.0.1` **[H: o Chrome do Windows continua a chegar a `localhost`; por confirmar pelo owner]**.

## Decisões recentes

- D-01 a D-18: ver [`analysis.md` §0](product/analysis.md#0-decisões-do-owner-passam-a-c).
- ADRs: ver [`docs/adr/`](adr/README.md). 15 aceites, 3 substituídos (0004 → 0013, 0009 → 0015, 0003 → 0018). Todos os ADRs do M01 estão decididos. M02: ADR-0014 (CI) **Proposto**, à espera da aprovação do owner.
- Harness: ver [`docs/engineering/claude-code-setup.md`](engineering/claude-code-setup.md), que inclui a proposta de servidores MCP, ainda sem nada instalado (instalação pede aprovação no M02, D-18).

## M02 · Core Foundation

Decomposto em 4 épicos e 17 tarefas → [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md).

- **E1 (concluído):** monorepo mínimo (`apps/api`, `apps/web`, `packages/contracts`) e Docker Compose; AC-01 verificada a partir de um clone limpo; fecha P-015 (fornecedor `fake` por omissão).
- **E2 (feita; CI verde no PR a 2026-11-23):** `.github/workflows/ci.yml` com 5 jobs que correm os mesmos scripts do local (`scripts/ci/*.sh`, `scripts/e2e.sh`), ADR-0014 (Proposto). Pint, Larastan nível 6 sem baseline, Pest (45), `tsc`, `oxlint`, Vitest (9), E2E (5). `apps/web` em Node 24 LTS. Falta: o owner activar *Secret scanning* + *Push protection* ([`ci.md`](engineering/ci.md)); mypy com o primeiro código Python.
- **E3 (feita, 2026-11-22):** contratos v1 em `packages/contracts` ([SPEC-003](specs/003-contratos-v1.md)): OpenAPI 3.1 (`tool-authorizations`, health), AsyncAPI 3.0 com 7 mensagens e envelope v1, 23 exemplos válidos e 69 inválidos. **E2.3:** job `contracts` na CI (`scripts/ci/contracts.sh`), com o validador numa imagem própria, sem rede. Decisões: o `turn.requested` leva a janela de contexto; o grant nunca vai no RabbitMQ; o taint é derivado só pelo Laravel; um grant por passo e aprovação consumida (revisão de segurança).
- **E4 (concluído; o E2E corre na CI desde a E2):** Identity & Access. P-017 fechada. `laravel/sanctum` instalado (SPA cross-origin). Fortify headless. `TotpLoginController` próprio (TOTP como alternativa à passkey). `SessionController`. Spec: [`docs/specs/002-identity-access.md`](specs/002-identity-access.md). Modelo de ameaças: [`docs/security/threat-model-identity-access.md`](security/threat-model-identity-access.md). 45 testes Pest a passar (E2). **E4.6b:** `scripts/e2e.sh` — 5 testes Playwright (AC-02a/b/c/e/f/g, T-02, T-03, T-07) numa stack descartável `kai-e2e`, passkey via Virtual Authenticator do CDP; registo de passkey na UI; `kai:enable-totp`. A revisão de segurança encontrou um achado ALTO (gestão de credenciais sem step-up, T-12), já corrigido: janela de 10 min e auditoria de credenciais. **UI mínima em `apps/web`** (login TOTP/recuperação/passkey, lista de sessões) — **primeiro ecrã do KAI visto e confirmado pelo owner num browser real** (Chrome, Windows), incluindo o login completo.

**Critério de aceitação:** AC-01 e AC-02; CI verde.

**Caminho crítico:** ~~E1.1 → E4.1 → E4.2 → E4.3 → E4.5 → E4.6a → E4.6b~~ — fechado. O M02 fica a depender só da CI verde no GitHub.

## Próximas 3 tarefas

1. Owner: activar *Secret scanning* + *Push protection*, aprovar o ADR-0014 e fazer merge do PR (fecha o M02).
2. M03: E4.1 (spec de Conversations, a partir do protótipo), E3.4b (deltas no Reverb, AC-004-10) e E3.5 (cancelamento). **E5.0 feito:** protótipo visual do chat com respostas simuladas ([SPEC-005](specs/005-prototipo-chat.md)); é a página inicial depois do login. Feitas: E1, E2.1 (RabbitMQ, [ADR-0018](adr/0018-mensageria-rabbitmq-outbox-retry-no-consumidor.md)), E2.2 (otel-lgtm, [`observability.md`](engineering/observability.md)), E3.1 ([SPEC-004](specs/004-ai-engine-m03.md)), E3.2 ([`apps/ai-engine`](../apps/ai-engine/README.md)) E3.3 (LLM Gateway: `fake`, Anthropic com SDK `anthropic` 2.6.0, Ollama; tabela de preços versionada) e E3.4a (consumidor de `turn.requested` com inbox num Redis próprio, orçamento, retry, timeout e eventos com confirms; reconexão própria ao RabbitMQ). Owner: para ter o RabbitMQ, o Redis da inbox, o AI Engine e o Grafana em dev, gerar as passwords com `scripts/dev/passwords.sh` (há uma nova, `KAI_AI_ENGINE_REDIS_PASSWORD`).
3. Owner: a BD de dev foi apagada por engano a 2026-11-23 (um `docker compose down -v` do agente caiu na stack de dev) e já foi recriada e migrada, mas está vazia. Recriar o owner (`kai:create-owner`), correr `kai:enable-totp` e registar de novo a passkey no Chrome/Windows Hello.

## Perguntas abertas

- P-015, P-017: **fechadas (2026-11-20)** → [`.env.example`](../.env.example) e [`docs/milestones/M02-core-foundation.md`](milestones/M02-core-foundation.md) (E4.1).
- Restantes P-xxx: ver [`analysis.md` §4.2](product/analysis.md#42-decisões-pendentes); nenhuma bloqueia o M02.
- Proposta MCP aprovada (D-18); a instalação pede nova aprovação explícita no M02, ainda não pedida: ver [`claude-code-setup.md` §5](engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado).

## Bloqueios

Nenhum.
