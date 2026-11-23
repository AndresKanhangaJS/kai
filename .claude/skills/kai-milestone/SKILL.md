---
name: kai-milestone
description: Decompõe um milestone do roadmap do KAI (M01 a M10) em épicos e depois em tarefas pequenas e verificáveis. Cada tarefa leva critérios de aceitação, dependências, riscos e plano de verificação. Usa quando se iniciar um milestone, quando o owner disser "planeia o M0X", "decompõe o milestone", "que tarefas faltam", "breakdown", ou quando for preciso estimar depois de decompor.
---
# kai-milestone: decomposição de milestone

Fonte: `docs/product/analysis.md` §7 (objectivo, entregáveis, critério e dependências de cada milestone) e PDF p.17–18.

## Procedimento
1. **Pré-condições:**
   - confirma que as dependências do milestone estão concluídas (`docs/STATUS.md`);
   - confirma que as P-xxx marcadas para este milestone estão fechadas ou têm uma recomendação aceite.
   - Se não estiverem, lista-as e pára.
2. **Objectivo:** reescreve-o numa frase e indica o critério de aceitação do milestone.
3. **Épicos:** 3 a 7, cada um com:
   - um resultado demonstrável;
   - os FR e NFR que cobre;
   - os ADRs que aplica ou que precisa de criar.
4. **Tarefas por épico:**
   - pequenas: cabem num PR revisível; se precisarem de mais de ~400 linhas de diff, dividem-se;
   - verbo + objecto + resultado verificável ("Adiciona tabela outbox com relay e teste de publicação");
   - cada uma com critério de aceitação (Given/When/Then ou comando de verificação), dependências e tipo (spec, contrato, código, teste, docs, infra);
   - a primeira tarefa de cada épico com comportamento novo é a spec (`kai-spec`); a de cada contrato novo é `kai-contract`.
5. **Ordem:**
   - ordena por dependências, primeiro o caminho crítico;
   - assinala o que pode correr em paralelo.
6. **Riscos:** os específicos do milestone, com probabilidade, impacto e mitigação; liga aos riscos da análise §4.3.
7. **Verificação do milestone:**
   - como se demonstra a entrega: comandos, testes E2E, avaliações, demo com dados sintéticos;
   - que documentação e ADRs ficam actualizados.
8. **Estimativa:** só depois da decomposição e só se o owner pedir (PDF p.18). Por tarefa, em intervalos, com as incertezas explícitas.
9. Escreve em `docs/milestones/M<NN>-<nome>.md` (cria a pasta se for o primeiro) e actualiza `docs/STATUS.md` com a skill `/status`.

## Formato
```
# M<NN>: <nome>
Objectivo / critério de aceitação / dependências / P-xxx resolvidas

## Épico E1: <resultado>  (FR-xxx, NFR-xxx, ADR-xxxx)
| ID | Tarefa | Tipo | Critério de aceitação | Depende de | Paralelo? |

## Riscos
## Verificação do milestone
```

## Regras
- Não planeies infra ou pastas "para depois". Cada tarefa responde a um critério deste milestone (PDF p.16).
- Se a decomposição revelar uma decisão arquitectural nova, cria uma P-xxx ou um ADR antes de continuar.
