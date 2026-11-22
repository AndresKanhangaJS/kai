# M02: Core Foundation

**Objectivo:** ter um monorepo mínimo a correr localmente com um comando — Laravel 13 e React a dialogar, MySQL e Redis saudáveis, o owner a autenticar-se por passkey (ou TOTP), contratos v1 definidos e uma CI verde — para o M03 (KAI Intelligence) arrancar sobre uma base testável.

**Critério de aceitação (`analysis.md` §7):** AC-01 e AC-02 (`docs/specs/001-mvp-fatia-vertical.md`); CI verde.

**Dependências:** M01 (Product Discovery), **concluído** a 2026-11-20 — PRD e ADRs aprovados, SPEC-001 aprovada.

**P-xxx resolvidas neste milestone:** P-015 (demo/CI sem chaves), P-017 (passkeys no Laravel 13).

**Nota sobre pré-condições:** nenhuma das duas P-xxx está fechada ainda — fechá-las é o próprio trabalho de T1.3 (P-015) e T4.1 (P-017), tal como aconteceu no M01 com P-003 a P-008. Nenhuma outra dependência está pendente.

**Mudança de âmbito face ao `docs/STATUS.md` da missão de arranque:** esse documento dizia para não criar CI nem a estrutura `apps/` durante a missão de arranque do harness (já concluída). O M02 é precisamente o milestone que as introduz — não há contradição, só a passagem de fase.

---

## Épico E1: monorepo mínimo e Docker Compose (NFR-007, NFR-008, NFR-029; D-03)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E1.1 | ~~Cria a estrutura mínima do monorepo~~ | infra | **Feito (2026-11-20).** `apps/api` (Laravel 13.11.0, scaffolded via Docker com PHP 8.5.13 — sem PHP/Composer instalados localmente), `apps/web` (Vite 8 + React 19 + TypeScript), `packages/contracts` (só README). `vendor/`/`node_modules/` confirmados fora do staging (`git add -n`) | — | Não |
| E1.2 | ~~Define `docker-compose.yml`~~ | infra | **Feito (2026-11-20).** `docker compose config` válido; os 4 serviços (api, web, mysql, redis) têm *health check* e passam a `healthy`; testado com `docker compose up -d` real (api e web respondem 200 no host), depois desmontado (`down -v`) | E1.1 | Não |
| E1.3 | ~~Cria `.env.example`~~ | infra/docs | **Feito (2026-11-20).** `.env.example` na raiz, sem segredos reais, com `MODEL_PROVIDER=fake` por omissão; `analysis.md` §4.2 marca P-015 "Fechado" | E1.2 | Não |
| E1.4 | ~~Verifica AC-01 de ponta a ponta~~ | teste (E2E/infra) | **Feito (2026-11-20).** AC-01 passa: `git clone` real para `/tmp` (sem `.env`, só `.env.example`), `docker compose up -d --build`, 4 serviços `healthy` em 49 s (≪ 10 min, NFR-029), `api` responde 200 e usa mesmo o MySQL (`DB::connection()->getName()` → `mysql`). Ver nota abaixo sobre o bug encontrado e corrigido | E1.3 | Não |

**Nota sobre um falso positivo na E1.2:** o teste feito na E1.2 (directamente no repositório de trabalho, que já tinha um `.env` e um `database.sqlite` deixados pelo scaffold original) deu `healthy` e 200, mas por uma razão errada. `php artisan serve` filtra as variáveis de ambiente que passa ao processo que serve os pedidos — só reenvia as que já existem no ficheiro `.env`, nunca as que só estão definidas no Docker Compose. Como o `.env` antigo tinha `DB_CONNECTION=sqlite` e o ficheiro sqlite existia e estava migrado, os pedidos foram servidos por SQLite, não por MySQL, apesar de a configuração dizer o contrário. A E1.4, ao partir de um clone limpo sem esse `.env`/sqlite residual, expôs o problema (erro 500: "Database file ... does not exist"). Corrigido no `apps/api/Dockerfile`: troca `php artisan serve` por `php -S` directo com o router do Laravel, que herda o ambiente completo do contentor. Re-confirmado nos dois sítios (clone limpo e repositório de trabalho) que a app usa mesmo o MySQL.

## Épico E2: CI (lint, análise estática, testes, validação de schemas, secret scan)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E2.1 | ~~Workflow CI do Laravel: Pint (lint), PHPStan/Larastan, Pest~~ | ci | **Feito localmente (2026-11-22); a confirmar no primeiro PR.** `scripts/ci/api.sh`: Pint, Larastan 3.14.0 no nível 6 sem baseline (22 erros corrigidos, nenhum ignorado) e Pest 4.7.8 (41 testes). Falha com exit 1 perante um erro injectado | E1.1 | Sim |
| E2.2 | ~~Workflow CI do React: lint, Vitest~~ | ci | **Feito localmente (2026-11-22).** `scripts/ci/web.sh`: `tsc -b`, `oxlint` (mantido em vez de ESLint/Prettier, decisão do owner) e Vitest 5.1.0 (9 testes: cliente WebAuthn e página de login). `apps/web` passa a Node 24 LTS. O `scripts/e2e.sh` corre também na CI | E1.1 | Sim |
| E2.3 | Workflow CI de contratos: valida os schemas OpenAPI/AsyncAPI/JSON Schema de `packages/contracts` | ci | Falha se um schema for inválido ou um exemplo não validar contra ele | E3.3 | Não |
| E2.4 | Secret scanning | ci | Bloqueia o merge se encontrar um segredo (NFR-007). **Feito do lado do repo (2026-11-22):** o `validate_harness.py` corre na CI. **Falta o owner activar *Secret scanning* + *Push protection* no GitHub** ([`ci.md`](../engineering/ci.md)); o gitleaks não foi aprovado (ADR-0014) | E1.1 | Sim |

## Épico E3: contratos v1 (FR-032 subconjunto, NFR-006; ADR-0002)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E3.1 | Define o contrato síncrono (OpenAPI 3.1) com `kai-contract`: `POST /internal/v1/tool-authorizations`, `/health/live`, `/health/ready` | contrato (`kai-contract`) | Schema em `packages/contracts/`, validado sintacticamente | — | Sim |
| E3.2 | Define os schemas AsyncAPI 3.x + JSON Schema das 6 mensagens do MVP (`ai.conversation.turn.*`, `ai.mission.step.*`, `ai.model.usage.recorded.v1`) com `kai-contract`, mesmo sem o RabbitMQ ainda (chega no M03) | contrato (`kai-contract`) | Schemas em `packages/contracts/`, com o envelope comum (`id`, `type`, `occurred_at`, `correlation_id`, `causation_id`, `idempotency_key`, `producer`, `traceparent`) | — | Sim |
| E3.3 | Escreve exemplos válidos e inválidos de cada schema (E3.1, E3.2), para a CI de contratos (E2.3) | teste/contrato | Cada schema tem ≥ 1 exemplo válido e ≥ 1 inválido | E3.1, E3.2 | Não |

## Épico E4: Identity & Access — login passkey + TOTP (FR-044, FR-045, FR-051; AC-02)

| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |
|---|---|---|---|---|---|
| E4.1 | ~~Spike: passkeys (WebAuthn) no Laravel 13~~ | spike/docs | **Feito (2026-11-20).** Suporte de 1.ª parte confirmado: `laravel/fortify` v1.43.0 + `laravel/passkeys` v0.3.0 (MIT), instalado em `apps/api` com aprovação explícita do owner (dependência nova). Cobre também o TOTP de D-05. `analysis.md` §4.2 marca P-017 "Fechado" | E1.1 | Não |
| E4.2 | ~~Escreve a spec de Identity & Access~~ | spec (`kai-spec`) | **Feito (2026-11-20).** `docs/specs/002-identity-access.md` (Aprovada), 7 critérios (AC-02a–g). Modelo de ameaças feito a seguir: `docs/security/threat-model-identity-access.md` (11 ameaças STRIDE, 9 testes a criar) | E4.1 | Não |
| E4.3 | ~~Migração `users`, `sessions`, `user_preferences`~~ | migração (`kai-db-migration`) | **Feito (2026-11-20).** `user_preferences` nova (único por `user_id`, FK cascade); `sessions` ganha `last_authenticated_at` e FK a `users` (cascade). `users`/`sessions` base já vinham do scaffold; `passkeys` e `two_factor_*` já vêm das migrações dos pacotes (E4.1). Verificado `migrate → rollback → migrate` contra o MySQL real (Docker Compose), não só SQLite; 4 testes PHPUnit novos (6/6 a passar) | E4.2 | Não |
| E4.4 | ~~Comando `artisan` para criar o owner por CLI~~ | código + testes (PHPUnit; Pest chega no E2) | **Feito (2026-11-20).** `kai:create-owner {name} {email} [--force]`: sem password (nullable, migração nova), preferências por omissão `pt`/`dark`, recusa duplicados e um 2.º owner sem `--force`. Não existe nem nunca existiu rota de registo público. 5 testes novos, 11/11 a passar | E4.3 | Sim |
| E4.5 | ~~Implementa login com TOTP (alternativa à passkey) e revogação de sessão~~ | código + testes (PHPUnit; Pest chega no E2) | **Feito (2026-11-20).** `laravel/sanctum` instalado (SPA cross-origin, dependência nova aprovada); Fortify configurado headless (sem views, sem password/registo); `TotpLoginController` próprio (o Fortify só tem TOTP como 2.º factor pós-password, que não existe aqui); `SessionController` (listar/revogar); auditoria por log estruturado + `last_authenticated_at`. 23 testes de integração a passar (AC-02b–g; T-01/04/05/06/08/10 do threat model). Verificado também contra MySQL real, com um pedido HTTP completo (CSRF+cookies). AC-02a (passkey) e T-02/T-03/T-07(cookies) ficam para a E4.6 (E2E) — ver notas abaixo | E4.3, E4.1 | Não |
| E4.6a | ~~UI mínima de login em `apps/web`~~ | código (React/TS) | **Feito (2026-11-20).** Login (TOTP + código de recuperação + botão de passkey), lista de sessões com revogar. Paleta de `identidade-visual.md`. **Verificado pelo owner no browser real** (Chrome, Windows): CORS, CSRF, cookie de sessão, login TOTP e `last_authenticated_at` todos a funcionar de ponta a ponta | E4.5 | Não |
| E4.6b | Teste E2E de AC-02 (Playwright) | teste (E2E) | AC-02 passa de ponta a ponta, via CI (E2.2); inclui o login por passkey (Virtual Authenticator do CDP) que a E4.5 não conseguiu testar ao nível de integração | E4.4, E4.5, E4.6a, E2.2 | Não |
| | | | **Feito (2026-11-21); corre na CI desde a E2 (job `e2e`).** `scripts/e2e.sh` corre 5 testes Playwright (AC-02a/b/c/e/f/g, T-02, T-03, T-07) numa stack descartável `kai-e2e` (override `docker-compose.e2e.yml`), com o Chromium da imagem oficial `mcr.microsoft.com/playwright:v1.65.1-noble` (fixada por digest) e `@playwright/test` 1.65.1 (dependências aprovadas pelo owner). Passkey real via Virtual Authenticator do CDP. O script confirma a auditoria no log do contentor (método de cada login, registo da passkey, sem segredos). **Lacuna fechada:** o owner não tinha como obter uma credencial → `kai:enable-totp` (CLI) e botão "Registar passkey". **Revisão de segurança (corrigido):** gestão de credenciais sem step-up (T-12 novo, ALTO) → `password.confirm` com janela de 10 min; auditoria de alterações de credenciais e `method` nos logins; `--force` revoga sessões e `--revoke-passkeys`; logs do E2E isolados do `laravel.log` de dev; `npm ci --ignore-scripts` antes de haver segredos no ambiente; portas de dev só em `127.0.0.1`. Re-revisão: sem bloqueantes; 3 achados menores corrigidos (auditoria da revogação pela CLI, "remember me" não conta como confirmação, 2 rotas a mais no teste de regressão). 42 testes PHPUnit | | |

**Achado na E4.4, relevante para toda a E2 (CI):** o `apps/api/phpunit.xml` tenta forçar `DB_CONNECTION=sqlite` para os testes, mas o Docker Compose já define `DB_CONNECTION=mysql` como variável de ambiente real do contentor. O `<env force="true">` do PHPUnit corrige `getenv()`, mas não `$_ENV`/`$_SERVER` — e o `env()` do Laravel lê esses primeiro. Resultado: os testes corriam silenciosamente contra o MySQL real (confirmado: a tabela `migrations` aparecia preenchida em `batch 1` depois de uma simples corrida de testes, sem eu ter corrido `migrate`). Isolados em transacções, não deixavam dados, por isso não se notava sem investigar. **Correcção, para já:** correr os testes com as variáveis forçadas ao nível do próprio `docker compose run`, não só do `phpunit.xml`:
```
docker compose run --rm -e APP_ENV=testing -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: api vendor/bin/phpunit
```
Confirmado depois desta mudança: a tabela `migrations` nem chega a existir no MySQL real durante os testes. Formalizado na E2: `scripts/ci/api.sh`, mais uma guarda no `tests/TestCase.php` que aborta qualquer teste fora do SQLite em memória.

**Achado na E4.6a, só visível num browser real (o `curl` não o apanha — CORS é imposto pelo browser, não pelo servidor):** `config/cors.php` tinha `'login'` na lista de `paths`, mas isso só cobre a rota exacta `/login`, não `/login/totp` (padrão `Str::is`, sem *wildcard*). O *preflight* do browser para `/login/totp` falhava silenciosamente, dando "Falha inesperada" na UI. O owner apanhou isto ao testar a sério no Chrome — exactamente o tipo de problema que só aparece ao usar a funcionalidade num browser, não em testes automáticos nem em `curl`. Corrigido: `'login/*'` adicionado aos `paths`. Confirmado com um *preflight* `OPTIONS` real e, a seguir, um login completo no browser do owner.

**Achado grave na E4.5, que invalidava as verificações "reais" de E1.2 a E4.4:** depois de trocar `php artisan serve` por `php -S` (E1.4), o *router* do Laravel (`vendor/.../resources/server.php`) resolve `public/index.php` a partir de `getcwd()`, não do `-t public` passado na linha de comandos. Como o `WORKDIR` do contentor é `/app`, **todos os pedidos HTTP, incluindo `/`, davam um erro fatal do PHP** ("require_once /app/index.php: No such file or directory") — mas com HTTP 200 (o PHP com `display_errors` liga devolve a página de erro como HTML normal). O healthcheck (`file_get_contents(...) !== false`) e os meus próprios `curl` anteriores só confirmavam "houve resposta", nunca o conteúdo — por isso isto passou despercebido desde a E1.4. Só apareceu ao tentar um pedido real a `/sanctum/csrf-cookie` com verificação do corpo da resposta. **Corrigido:** o `CMD` do Dockerfile muda para a pasta `public/` antes de invocar `php -S` (é assim que o próprio `artisan serve` o faz, via `cwd = public_path()` no Symfony Process). O healthcheck do `api` passou a confirmar que a resposta **não** é uma página de erro fatal, não só que respondeu. Reconfirmado com um pedido real de ponta a ponta (CSRF cookie → login TOTP → listar sessões), contra o MySQL real.

---

## Ordem e caminho crítico

1. **Caminho crítico até AC-02:** ~~E1.1 → E4.1 → E4.2 → E4.3 → E4.5 → E4.6a → E4.6b~~ (E2E com passkey real, a passar localmente; só falta ligá-lo à CI na E2.2).
2. **Em paralelo com o caminho crítico:** E1.2 → E1.3 → E1.4 (AC-01); E2.1, E2.2, E2.4; E3.1, E3.2 → E3.3 → E2.3; E4.4.
3. O milestone só fecha quando AC-01, AC-02 e a CI completa (E2.1–E2.4) estiverem todos verdes.

## Riscos

| Risco | P/I | Mitigação |
|---|---|---|
| O spike de passkeys (E4.1) revela que o Laravel 13 não tem suporte nativo suficiente | M/M | Se exigir um pacote novo, isso é uma dependência nova (regra de ouro, `security.md`) — pára e pede aprovação antes de a adicionar; TOTP já é o plano B funcional |
| CI verde vira critério vago e o scope cresce (lint extra, cobertura, etc.) | M/M | Scope creep (`analysis.md` §4.3): a CI do M02 cobre só o que está listado em §7 (lint, PHPStan, mypy, Pest, Vitest, validação de schemas, secret scan) — nada mais sem pedido explícito |
| Contratos v1 (E3) desenhados sem o consumidor (AI Engine) ainda existir, e ficarem errados quando o M03 os usar | M/M | `kai-contract` corre com os exemplos (E3.3) validados nos dois lados; qualquer alteração incompatível no M03 cria uma nova major, nunca edita a v1 em silêncio (ADR-0002) |
| `docker compose up` ultrapassa os 10 min (NFR-029) à medida que mais serviços entram | B/M | Medir já no E1.4; se falhar, é sinal para rever imagens/healthchecks antes de continuar |

## Verificação do milestone

- `docker compose up` num clone limpo deixa todos os serviços *healthy* em ≤ 10 min, sem segredos no repositório (AC-01).
- O owner cria-se por CLI, autentica-se por passkey (ou TOTP), e uma sessão revogada deixa de funcionar (AC-02).
- CI verde: Pint, PHPStan, Pest (`apps/api`); ESLint, Vitest (`apps/web`); validação de schemas (`packages/contracts`); secret scan.
- `packages/contracts` tem o contrato síncrono e os 6 schemas assíncronos do MVP, cada um com exemplos válidos e inválidos.
- `docs/product/analysis.md` §4.2: P-015 e P-017 marcados "Fechado".
- `docs/STATUS.md` actualizado a reflectir o M02 fechado e a abertura do M03.

## Estimativa

Não incluída (PDF p.18). Pede-a explicitamente se a quiseres por tarefa.
