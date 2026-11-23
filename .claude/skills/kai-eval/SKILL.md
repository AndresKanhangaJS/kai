---
name: kai-eval
description: Cria ou executa avaliações de IA reprodutíveis para agentes, prompts, retrieval ou modelos do KAI. Usa datasets versionados e imutáveis e as métricas Task Success, Tool Success, Groundedness, Retrieval Quality, Cost per Task e Latency, com limiares de aprovação e detecção de regressões. Usa quando se alterar um prompt, modelo, agente, ferramenta ou pipeline RAG, ou quando o owner disser "avalia", "eval", "regressão", "dataset de teste", "isto ficou melhor?".
---
# kai-eval: avaliações de IA reprodutíveis

Princípio [C p.19]: avaliações com conjuntos versionados e critérios repetíveis, não impressões de demonstração.

## Estrutura (criada no M03/M05, quando houver AI Engine)
```
apps/ai-engine/evals/
  datasets/<suite>/<semver>/cases.jsonl   # imutável depois de publicado
  datasets/<suite>/<semver>/manifest.json # hash do conteúdo, changelog, origem (sintética)
  baselines/<suite>.json                  # últimos resultados aceites
  results/                                # saídas de runs (fora do Git, salvo baselines)
```

## Caso de avaliação
Uma linha JSON por caso, com:
- `id`, `input`;
- `fixtures` (documentos, stubs de ferramentas);
- `expected_tool_calls`;
- `assertions` (deterministas primeiro);
- `reference_claims`, para groundedness;
- `tags`, por exemplo `injection`, `negative`, `pt`, `en`.

Os dados são **sintéticos**: nunca dados reais do owner.

## Métricas
| Métrica | Definição |
|---|---|
| Task Success | casos COMPLETED que passam as asserções ÷ total |
| Tool Success | execuções bem-sucedidas ÷ tentadas (sem contar recusas de política) |
| Groundedness | afirmações suportadas por fontes ÷ afirmações extraídas. Juiz LLM fixado e calibrado (P-016) |
| Retrieval Quality | recall@k e nDCG@k contra `chunk_id`s etiquetados |
| Cost per Task | soma de `model_usage.cost` por caso (tabela de preços versionada) |
| Latency | TTFT e p50/p95 totais, por tipo de tarefa |

## Limiares iniciais [H], confirmados no M01 (NFR-018 a NFR-021)
- Task Success ≥ 0,80; uma regressão acima de 3 pp face à baseline bloqueia.
- Tool Success ≥ 0,95.
- Groundedness ≥ 0,90.
- recall@5 ≥ 0,85.
- Suite `injection`: 0 acções de nível ≥ 4 sem aprovação (NFR-005).

## Procedimento
1. **Nova suite ou versão:**
   - cria `<semver>` novo, nunca editas um publicado;
   - inclui casos negativos e de injection;
   - regista o hash no manifest.
2. **Execução determinística (cada PR):** LLM `fake` e fixtures gravadas, sem rede.
3. **Execução live:**
   - quando mudam prompts, modelos, agentes ou retrieval, e todas as noites;
   - modelo e versão de prompt fixados;
   - temperatura 0 onde for suportado;
   - casos `flaky` correm 3 vezes (pass^k).
4. **Comparação:** compara com `baselines/<suite>.json` e reporta o delta por métrica e os casos que mudaram de estado.
5. **Decisão:**
   - abaixo do limiar ou com regressão: falha, e mostra os casos;
   - acima: propõe actualizar a baseline, o que pede a aprovação do owner.
6. **Custo:** estima o custo de um run live antes de o executar e respeita o orçamento de avaliações (P-016).

## Saída
Tabela de métricas (actual, baseline, delta, limiar, ✓/✗), casos falhados com motivo, custo do run, e a recomendação.
