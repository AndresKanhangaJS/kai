# Workflow Git (global)

- Antes de mexer em ficheiros, confirma a branch com `git branch --show-current`. Nunca trabalhes directamente em `main`.
- Branch por milestone ou tarefa: `feat/mNN-<tema>`, `fix/<tema>`, `docs/<tema>`, `chore/<tema>`.
- Commits pequenos e atómicos, com uma intenção cada; testes e docs vão no mesmo commit do código a que dizem respeito.
- Formato Conventional Commits: `tipo(âmbito opcional): descrição em PT-PT no imperativo`.
  - Exemplos: `feat(missions): adiciona estado AWAITING_APPROVAL`, `docs(adr): regista ADR-0009`.
  - Mudanças incompatíveis: `!` após o tipo e rodapé `BREAKING CHANGE:`.
- Só fazes commit depois de o owner aprovar a fase ou entrega. Push e PR pedem confirmação explícita.
- Proibido: `--force` / `-f` no push, `--no-verify`, reescrever histórico partilhado, apagar branches remotas.
- Antes de propor um commit, mostra `git status` e `git diff --stat`, sem segredos nem ficheiros gerados.
- O PR usa `.github/pull_request_template.md` e liga a spec, os ADRs e a evidência dos testes.
- Ficheiros grandes, binários ou gerados não entram no Git, salvo o PDF de produto e assets aprovados.
