---
name: status
description: Actualiza docs/STATUS.md com o milestone actual, as decisões recentes, as próximas 3 tarefas, as perguntas abertas e os bloqueios. Uso manual com /status no fim de uma sessão, fase ou entrega.
disable-model-invocation: true
---
# /status: actualizar docs/STATUS.md

## Fontes (lê antes de escrever)
1. `docs/STATUS.md`, a versão actual.
2. `git branch --show-current`, `git status --short` e `git log --oneline -10`.
3. `docs/adr/README.md`: ADRs novos ou que mudaram de estado.
4. `docs/product/analysis.md` §4.2: P-xxx fechadas ou novas.
5. O que foi feito nesta sessão, só se houver evidência (ficheiros, comandos, testes).

## Conteúdo obrigatório (mantém as secções e a ordem)
1. **Cabeçalho:** data (AAAA-MM-DD), milestone actual, branch, estado dos commits (por commitar, commitado, push).
2. **Fases / milestone:** tabela de estado. Só marca "concluído" com evidência; se não houver, escreve "por verificar".
3. **Decisões recentes:** ADRs e D-xx novos, com link.
4. **Próximas 3 tarefas:** ordenadas, cada uma com critério de aceitação numa linha.
5. **Perguntas abertas:** P-xxx que bloqueiam as próximas tarefas (as restantes ficam só como link para a análise).
6. **Bloqueios:** o que impede de avançar e quem decide.

## Regras
- Máximo ~80 linhas: o ficheiro é importado no `CLAUDE.md` e custa contexto em cada sessão.
- Não inventes progresso. O que não foi verificado escreve-se como "por verificar".
- Sem segredos nem dados pessoais.
- Mostra o diff ao owner antes de terminar. Não faças commit.
