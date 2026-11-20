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
| E2.1 | Workflow CI do Laravel: Pint (lint), PHPStan/Larastan, Pest | ci | CI corre em cada PR; falha se algum passo falhar | E1.1 | Sim |
| E2.2 | Workflow CI do React: ESLint/Prettier, Vitest | ci | Idem, para `apps/web` | E1.1 | Sim |
| E2.3 | Workflow CI de contratos: valida os schemas OpenAPI/AsyncAPI/JSON Schema de `packages/contracts` | ci | Falha se um schema for inválido ou um exemplo não validar contra ele | E3.3 | Não |
| E2.4 | Secret scanning na CI (ex. gitleaks) | ci | Bloqueia o merge se encontrar um segredo (NFR-007) | E1.1 | Sim |

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
| E4.3 | Migração `users`, `sessions`, `user_preferences` com `kai-db-migration`, `user_id` em todas as linhas próprias | migração (`kai-db-migration`) | Migração reversível; índice único onde aplicável; dados de teste sintéticos | E4.2 | Não |
| E4.4 | Comando `artisan` para criar o owner por CLI (sem registo público, D-05) | código + testes Pest | Comando cria um utilizador; não existe rota de registo público | E4.3 | Sim |
| E4.5 | Implementa login com passkey (ou TOTP como alternativa) e revogação de sessão | código + testes Pest | AC-02 passa a nível de integração; sessão revogada deixa de autenticar pedidos | E4.3, E4.1 | Não |
| E4.6 | Teste E2E de AC-02 (Playwright) | teste (E2E) | AC-02 passa de ponta a ponta, via CI (E2.2) | E4.4, E4.5, E2.2 | Não |

---

## Ordem e caminho crítico

1. **Caminho crítico até AC-02:** ~~E1.1 → E4.1 → E4.2~~ → E4.3 → E4.5 → E4.6.
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
