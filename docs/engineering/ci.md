# CI do KAI

Decisão e alternativas: [ADR-0014](../adr/0014-ci-github-actions-via-docker-compose.md). Workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

## O que corre

A CI e o local correm exactamente os mesmos scripts, dentro das imagens do Docker Compose. A excepção é o job `contracts`, que usa a imagem fixada em `packages/contracts/tooling/`. As imagens são só para x86_64: o lock de Python tem hashes de wheels linux x86_64.

| Job | Script | Passos |
|---|---|---|
| `harness` | `scripts/ci/harness.sh` | `validate_harness.py` (estrutura do harness + scan de segredos) e testes do hook `guard.sh` |
| `contracts` | `scripts/ci/contracts.sh` | Contratos v1 (E2.3): JSON Schemas, OpenAPI 3.1 e AsyncAPI 3.0 contra os meta-schemas oficiais, `$ref`, exemplos válidos e inválidos, regras do KAI ([`packages/contracts`](../../packages/contracts/README.md)) |
| `api` | `scripts/ci/api.sh` | `composer audit` (avisos de segurança do lock; precisa de rede), Pint (`--test`), PHPStan/Larastan nível 6, Pest (SQLite em memória, forçado no `docker compose run`) |
| `integration` | `scripts/ci/integration.sh` | Pest `tests/Integration` contra o RabbitMQ (M03 E2.1) e o `otel-lgtm` (M03 E2.2) reais, numa stack descartável `kai-it`, com passwords aleatórias em cada corrida e o Grafana numa porta efémera; verifica também que os dois recusam arrancar com passwords fracas ([`rabbitmq.md`](rabbitmq.md), [`observability.md`](observability.md)) |
| `web` | `scripts/ci/web.sh` | `npm ci`, `tsc -b`, `oxlint`, Vitest |
| `e2e` | `scripts/e2e.sh` | AC-02 em Playwright, numa stack descartável `kai-e2e` |

O workflow corre em cada `pull_request` e em cada `push` para `main`. Tem só permissão de leitura e não usa segredos do repositório.

## Correr localmente

```bash
scripts/ci/harness.sh
scripts/ci/contracts.sh
scripts/ci/api.sh
scripts/ci/integration.sh               # pode correr com a stack de dev ligada
scripts/ci/web.sh
docker compose stop && scripts/e2e.sh   # o E2E usa as mesmas portas da stack de dev
scripts/ci/all.sh                       # tudo, pela ordem da CI
```

## Secret scanning (E2.4, NFR-007): passos para o owner

O scan de segredos na CI (`validate_harness.py`) procura 10 padrões em todos os ficheiros que o git conhece, mas só na árvore final do PR, não em cada commit. A protecção principal é a do próprio GitHub, que se activa nas definições do repositório:

1. **Settings → Code security → Secret Protection → Enable.** Isto activa o *Secret scanning*: o GitHub analisa o histórico e os pushes novos.
2. Na mesma página, activa a **Push protection**: um push que contenha um segredo conhecido é bloqueado antes de chegar ao repositório.
3. Em repositórios públicos, as duas são gratuitas. Num repositório privado exigem GitHub Advanced Security (Secret Protection).

## Branch protection (opcional, recomendado)

**Settings → Branches → Add rule** para `main`:
- Require a pull request before merging.
- Require status checks to pass, com os 6 jobs: `Harness e scan de segredos`, `Contratos (schemas, OpenAPI, AsyncAPI, exemplos)`, `API (Pint, PHPStan, Pest)`, `Integração (RabbitMQ)`, `Web (tsc, oxlint, Vitest)` e `E2E AC-02 (Playwright)`.

## Manutenção
- Actualizar a `actions/checkout` (SHA), o digest de uma imagem ou a versão de uma ferramenta é uma alteração revista, com a fonte e a data no ADR-0014. Nunca é automática.
- Subir o nível do PHPStan pede uma decisão explícita. Hoje está no nível 6, sem baseline.
- Por fazer: o mypy entra com o primeiro código Python (M03). Os testes de produtor e consumidor dos contratos entram com o código que os usa (M03, M05).
