# CI do KAI

Decisão e alternativas: [ADR-0014](../adr/0014-ci-github-actions-via-docker-compose.md). Workflow: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

## O que corre

A CI e o local correm exactamente os mesmos scripts, dentro das imagens do Docker Compose.

| Job | Script | Passos |
|---|---|---|
| `harness` | `scripts/ci/harness.sh` | `validate_harness.py` (estrutura do harness + scan de segredos) e testes do hook `guard.sh` |
| `api` | `scripts/ci/api.sh` | Pint (`--test`), PHPStan/Larastan nível 6, Pest (SQLite em memória, forçado no `docker compose run`) |
| `web` | `scripts/ci/web.sh` | `npm ci`, `tsc -b`, `oxlint`, Vitest |
| `e2e` | `scripts/e2e.sh` | AC-02 em Playwright, numa stack descartável `kai-e2e` |

O workflow corre em cada `pull_request` e em cada `push` para `main`. Tem só permissão de leitura e não usa segredos do repositório.

## Correr localmente

```bash
scripts/ci/harness.sh
scripts/ci/api.sh
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
- Require status checks to pass, com os 4 jobs: `Harness e scan de segredos`, `API (Pint, PHPStan, Pest)`, `Web (tsc, oxlint, Vitest)` e `E2E AC-02 (Playwright)`.

## Manutenção
- Actualizar a `actions/checkout` (SHA), o digest de uma imagem ou a versão de uma ferramenta é uma alteração revista, com a fonte e a data no ADR-0014. Nunca é automática.
- Subir o nível do PHPStan pede uma decisão explícita. Hoje está no nível 6, sem baseline.
- Por fazer: a E2.3 (validação de schemas de `packages/contracts`) entra com a E3; o mypy entra com o primeiro código Python (M03).
