# Contribuir para o KAI

O KAI é um projecto pessoal em Product Discovery. Sugestões e issues são bem-vindas. Antes de proporem código, leiam:
- a visão: [`docs/product/kai-vision.md`](docs/product/kai-vision.md);
- a análise: [`docs/product/analysis.md`](docs/product/analysis.md);
- os ADRs: [`docs/adr/`](docs/adr/README.md).

## Como trabalhamos
1. **Spec**: requisito com critérios Given/When/Then.
2. **Plano.**
3. **Testes.**
4. **Implementação.**
5. **Revisão independente.**
6. **Docs/ADR.**
7. **Commit.**

Uma alteração está pronta quando cumpre a **Definition of Done** (ver `CLAUDE.md`).

## Convenções
- **Idioma:** PT-PT nos documentos e mensagens; identificadores de código em inglês (ADR-0012).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/), por exemplo `feat(missions): adiciona estado AWAITING_APPROVAL`.
- **Branches:** `feat/mNN-<tema>`, `fix/<tema>`, `docs/<tema>`, `chore/<tema>`.
- **PRs:** pequenos, com o template preenchido.
- **Decisões arquitecturais:** cada uma tem um ADR.
- **Proibido:** nunca reescrever histórico partilhado nem usar `git push --force`.

## Segurança
- Nunca incluas segredos, credenciais ou dados pessoais reais. Usa `.env.example` e dados sintéticos.
- Vulnerabilidades reportam-se em privado: ver [`SECURITY.md`](SECURITY.md).
