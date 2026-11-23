---
name: done
description: Verifica a Definition of Done do KAI sobre o diff actual e falha explicitamente se faltar algum ponto. Uso manual com /done antes de propor um commit ou PR.
disable-model-invocation: true
---
# /done: checklist de Definition of Done

## Âmbito
- Por omissão: `git diff` + `git diff --staged` + ficheiros novos (`git status --short`).
- Se o owner indicar um intervalo (ex.: `main...HEAD`), usa-o.

## Verificação (cada ponto exige evidência concreta)
| # | Ponto da DoD (PDF p.21) | Como verificar |
|---|---|---|
| 1 | O requisito está documentado e tem critérios de aceitação | Existe uma spec (`docs/specs/`) ou um FR com critérios Given/When/Then ligado à alteração. O link aparece no relatório. |
| 2 | A implementação respeita os limites de domínio e os contratos | Sem acessos entre módulos; contratos alterados passaram pela skill `kai-contract`; testes de arquitectura ou contrato passam (output). |
| 3 | Existem testes adequados e passam localmente | Cada critério tem um teste com o ID no nome; há casos negativos de segurança; output do comando de testes. **Antes do M02 não há toolchain: escreve "não aplicável" e justifica.** |
| 4 | Logs e erros sem dados sensíveis | Grep ao diff por logs de conteúdo, tokens e segredos; `.claude/rules/observability.md` cumprida. |
| 5 | A documentação foi actualizada | Docs, ADR e `STATUS.md` tocados quando necessário; links internos válidos. |
| 6 | A alteração foi revista antes de integrar | Existe uma revisão `kai-review` ou um relatório do `kai-verifier` para este diff, sem BLOQUEANTES em aberto. |

**Verificações adicionais:**
- Nenhum segredo no diff: procura padrões como `sk-`, `AKIA`, `BEGIN .*PRIVATE KEY`, `password=`, tokens.
- Nenhum ficheiro `.env` real.
- Nenhuma dependência nova sem aprovação registada.

## Saída
```
DoD: <âmbito>, <data>
Resultado: PASSA | FALHA (n pontos)

| # | Ponto | Estado (✓/✗/N/A) | Evidência |
|---|-------|------------------|-----------|

O que falta para passar:
- ...
```

## Regras
- **Um ponto sem evidência conta como ✗**, nunca como ✓ por omissão.
- "N/A" só com justificação explícita (ex.: só documentação, sem código).
- Não corrijas nada durante o /done: só reportas.
