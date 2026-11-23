# ADR-0014: CI em GitHub Actions via Docker Compose

- **Estado:** Proposto
- **Data:** 2026-11-22
- **Decisores:** owner
- **Relacionados:** ADR-0007 (baseline de versões; "matriz de versões na CI (M02)"), NFR-007 (segredos), M02 E2.1/E2.2/E2.3/E2.4, SPEC-003

## Contexto
- [C] O M02 só fecha com CI verde: lint, análise estática, testes e secret scan (`docs/milestones/M02-core-foundation.md`, §Verificação).
- [C] Na E4.4, os testes correram sem ninguém notar contra o MySQL real: o ambiente do contentor sobrepunha-se ao `phpunit.xml`. Um comando diferente na CI e no local volta a abrir esta classe de erro.
- [C] Regras do projecto: Pest e PHPStan/Larastan no `apps/api`; Vitest no `apps/web`. Toda a dependência, imagem ou action é supply chain: versão fixa, aprovação do owner (`security.md`).
- [C, decisões do owner, 2026-11-22] Manter o `oxlint` (vem do scaffold) em vez de ESLint/Prettier. Não usar o gitleaks; usar o *secret scanning* nativo do GitHub. Subir o `apps/web` para Node 24 LTS: o Node 20 está sem suporte desde 2026-04-30, e o Vitest 5 e o jsdom 31 exigem Node ≥ 22.

## Opções consideradas
1. **Scripts partilhados a correr nas imagens do Docker Compose:** a CI corre `scripts/ci/*.sh` e `scripts/e2e.sh`, tal como o local. Prós: paridade total; só uma action de terceiros. Contras: mais lenta, porque constrói as imagens.
2. **Actions nativas (`setup-php`, `setup-node`) a correr no runner:** mais rápida. Contras: mais actions de terceiros, um ambiente diferente do local e risco de repetir o bug da E4.4.
3. **ESLint + Prettier em vez de oxlint; gitleaks como secret scan; Vitest 3 em Node 20:** rejeitadas pelo owner (mais dependências; Node 20 sem suporte).

## Decisão
A CI corre em GitHub Actions com 5 jobs (`harness`, `contracts`, `api`, `web`, `e2e`). Cada um executa os mesmos scripts do repositório, dentro das imagens do Docker Compose (o `contracts` usa a imagem fixada em `packages/contracts/tooling/`). Regras:
- só `actions/checkout`, fixada por SHA de commit;
- `permissions: contents: read` e `persist-credentials: false`.

Ferramentas, todas com versão exacta e lockfile:
- **`apps/api`:** Pint, PHPStan com Larastan 3.14.0 no nível 6 e sem baseline, Pest 4.7.8, que fixa o PHPUnit em 12.5.33.
- **`packages/contracts` (E2.3):** `jsonschema` 4.26.0 e `PyYAML` 6.0.3 (MIT, com hashes), em `python:3.14-slim` fixada por digest. O OpenAPI e o AsyncAPI são validados contra os meta-schemas oficiais versionados, em vez de usar o `openapi-spec-validator`, que traria 20 pacotes (incluindo o Pydantic).
- **`apps/web`:** `tsc`, `oxlint` e Vitest 5.1.0 com Testing Library 16.3.3 e jsdom 31.0.0, sobre `node:24-alpine` fixada por digest.

O secret scan combina o *Secret scanning* e a *Push protection* do GitHub com o `validate_harness.py` na CI, que analisa todos os ficheiros conhecidos do git (`git ls-files`, nunca os ignorados) com 10 padrões.

Detalhes e desvios ao plano:
- todas as imagens (`composer`, `php`, `mysql`, `redis`, `node`, Playwright) ficam fixadas por digest;
- `npm ci --ignore-scripts` em todo o lado;
- o PHPStan analisa também `tests/`;
- a suite `Unit` vazia sai do `phpunit.xml` (só tinha o exemplo do scaffold); volta quando houver o primeiro teste unitário;
- Larastan 3.14.0 porque a 3.15.0 tinha menos de 2 semanas;
- `@testing-library/dom` entra como *peer dependency* obrigatória da `@testing-library/react`;
- o `tests/TestCase.php` recusa correr fora do SQLite em memória (bug da E4.4).

## Consequências
- **Positivas:** o que passa no local passa na CI e vice-versa. A supply chain da CI é mínima. O E2E com passkey corre em cada PR, numa stack descartável. Os testes deixam de poder correr contra o MySQL real.
- **Negativas / custos:** a CI é mais lenta, porque constrói as imagens em cada job, sem cache por agora. O scan de segredos na CI é mais fraco que o gitleaks e só vê a árvore final do PR, não cada commit; o histórico depende do *Secret scanning* do GitHub, que o owner tem de activar.
- **Riscos e mitigação:** os digests e SHAs fixados envelhecem; actualizá-los é uma alteração revista, nunca automática. Subir de nível no PHPStan pede um novo ADR ou uma revisão deste. O mypy entra com o código Python (M03).

## Verificação
- `.github/workflows/ci.yml` é revisto pelo `kai-security-reviewer` em cada alteração.
- O `scripts/ci/api.sh` falha (exit 1) com um erro de tipos injectado (verificado em 2026-11-22).
- Opcional: *branch protection* em `main` a exigir os 5 jobs (`docs/engineering/ci.md`).

## Fontes
- `actions/checkout` v7.0.1 → commit `3d3c42e5aac5ba805825da76410c181273ba90b1` (`git ls-remote` e data do commit, 2026-07-17; verificado em 2026-11-22).
- Packagist: `larastan/larastan` v3.14.0 (2026-11-03) e `pestphp/pest` v4.7.8 (2026-08-03), ambos MIT. npm: `vitest` 5.1.0 (2026-11-02), `jsdom` 31.0.0 (2026-11-05), `@testing-library/react` 16.3.3 e `@testing-library/dom` 10.4.2, todos MIT (verificado em 2026-11-22).
- `node:24-alpine@sha256:116b800c…`: Node v24.22.3 (verificado em 2026-11-22).
- `python:3.14-slim@sha256:9aaa4740…`: Python 3.14.10. PyPI: `jsonschema` 4.26.0 (2026-01-07), `PyYAML` 6.0.3 (2025-09-25), `referencing` 0.37.0, `rpds-py` 2026.9.1, `attrs` 26.1.0, `jsonschema-specifications` 2025.9.1, todos MIT. Meta-schemas: ver `packages/contracts/README.md` (verificado em 2026-11-22).
