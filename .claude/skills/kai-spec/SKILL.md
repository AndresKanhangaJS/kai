---
name: kai-spec
description: Escreve a especificação de uma funcionalidade do KAI antes de qualquer código. A spec tem contexto, requisitos FR/NFR referenciados, critérios Given/When/Then, segurança, observabilidade, plano de testes, fora de âmbito e perguntas abertas. Usa quando o owner pedir uma nova funcionalidade, épico ou alteração de comportamento, ou disser "escreve a spec", "especifica", "critérios de aceitação para…", "write a spec". É o primeiro passo obrigatório do workflow.
---
# kai-spec: especificação de funcionalidade

## Quando usar
- Antes de planear ou implementar qualquer funcionalidade, épico ou alteração de comportamento.
- Não usar para correcções triviais sem mudança de comportamento (typo, renomeação local).

## Entradas a ler primeiro
1. `docs/product/analysis.md`: FR-xxx, NFR-xxx, decisões D-xx, pendentes P-xxx, MVP (§6).
2. `docs/product/kai-vision.md`: a página do PDF de onde vem o requisito.
3. Os ADRs relevantes em `docs/adr/`.
4. Specs existentes em `docs/specs/`, para evitar duplicados.

## Procedimento
1. Identifica os FR/NFR que a funcionalidade cobre. Se nenhum existir, **pára e pergunta**: não inventes requisitos.
2. Copia [templates/spec.md](templates/spec.md) para `docs/specs/<NNN>-<kebab-titulo>.md`. A numeração é sequencial; cria a pasta se não existir.
3. Preenche todas as secções. Etiqueta cada afirmação com [C] (com origem), [H] (com justificação) ou [P].
4. Critérios de aceitação:
   - formato Given/When/Then;
   - um comportamento por critério;
   - verificáveis por teste automático (indica o tipo: unit, integração, contrato, E2E, eval);
   - pelo menos um caso negativo de segurança quando há dados ou ferramentas.
5. Segurança:
   - indica o nível de operação (1–6) de cada acção;
   - dados tocados e o seu isolamento por `user_id`;
   - conteúdo não confiável envolvido;
   - ameaças relevantes; se forem não triviais, corre a skill `kai-threat-model`.
6. Observabilidade: spans, métricas e logs novos, com os nomes da regra `observability.md`.
7. Contratos: se tocar em OpenAPI ou AsyncAPI, indica-o e corre a skill `kai-contract` antes do código.
8. Fora de âmbito: lista explicitamente o que não entra.
9. Perguntas abertas: viram P-xxx; não avances com elas abertas se bloquearem um critério.
10. Apresenta a spec ao owner. Estado `Rascunho` até aprovação; depois passa a `Aprovada`.

## Saída
- O ficheiro da spec, mais um resumo de 5 linhas: objectivo, número de critérios, níveis de operação, contratos tocados, perguntas abertas.

## Regras
- Uma spec descreve **o quê** e **porquê**; o **como** fica no plano.
- Uma spec grande demais (mais de ~10 critérios) divide-se.
- Não escrevas código na spec, salvo exemplos de payload sintéticos.
