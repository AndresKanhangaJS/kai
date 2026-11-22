# ADR-0014: CI em GitHub Actions via Docker Compose

- **Estado:** Proposto
- **Data:** 2026-11-22
- **Decisores:** owner
- **Relacionados:** ADR-0007 (baseline de versões; "matriz de versões na CI (M02)"), NFR-007 (segredos), M02 E2.1/E2.2/E2.4

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
A CI corre em GitHub Actions com 4 jobs (`harness`, `api`, `web`, `e2e`). Cada um executa os mesmos scripts do repositório, dentro das imagens do Docker Compose. Regras:
- só `actions/checkout`, fixada por SHA de commit;
- `permissions: contents: read` e `persist-credentials: false`.

Ferramentas, todas com versão exacta e lockfile:
- **`apps/api`:** Pint, PHPStan com Larastan 3.14.0 no nível 6 e sem baseline, Pest 4.7.8, que fixa o PHPUnit em 12.5.33.
- **`apps/web`:** `tsc`, `oxlint` e Vitest 5.1.0 com Testing Library 16.3.3 e jsdom 31.0.0, sobre `node:24-alpine` fixada por digest.

O secret scan combina o *Secret scanning* e a *Push protection* do GitHub com o `validate_harness.py` na CI.

## Consequências
- **Positivas:** o que passa no local passa na CI e vice-versa. A supply chain da CI é mínima. O E2E com passkey corre em cada PR, numa stack descartável. Os testes deixam de poder correr contra o MySQL real.
- **Negativas / custos:** a CI é mais lenta, porque constrói as imagens em cada job, sem cache por agora. O scan de segredos na CI tem 6 padrões e é mais fraco que o gitleaks; depende de o owner activar as funcionalidades do GitHub.
- **Riscos e mitigação:** os digests e SHAs fixados envelhecem; actualizá-los é uma alteração revista, nunca automática. Subir de nível no PHPStan pede um novo ADR ou uma revisão deste. A E2.3 (validação de schemas) e o mypy entram quando existirem a E3 e o código Python.

## Verificação
- `.github/workflows/ci.yml` é revisto pelo `kai-security-reviewer` em cada alteração.
- O `scripts/ci/api.sh` falha (exit 1) com um erro de tipos injectado (verificado em 2026-11-22).
- Opcional: *branch protection* em `main` a exigir os 4 jobs (`docs/engineering/ci.md`).

## Fontes
- `actions/checkout` v7.0.1 → commit `3d3c42e5aac5ba805825da76410c181273ba90b1` (`git ls-remote` e data do commit, 2026-07-17; verificado em 2026-11-22).
- Packagist: `larastan/larastan` v3.14.0 (2026-11-03) e `pestphp/pest` v4.7.8 (2026-08-03), ambos MIT. npm: `vitest` 5.1.0 (2026-11-02), `jsdom` 31.0.0 (2026-11-05), `@testing-library/react` 16.3.3 e `@testing-library/dom` 10.4.2, todos MIT (verificado em 2026-11-22).
- `node:24-alpine@sha256:116b800c…`: Node v24.22.3 (verificado em 2026-11-22).
