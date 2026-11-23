# ADR-0006: Abstracção de LLM como porta própria

- **Estado:** Aceite (2026-11-20, D-08)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.8, p.14–15, p.20; ADR-0004; D-08

## Contexto
O PDF pede:
- modelos híbridos, com uma abstracção de fornecedores [C p.15, p.20];
- custos rastreados e limitados [C p.14];
- o LLM Gateway como componente Python [C p.8].

O owner escolheu Anthropic (cloud) + Ollama (local) para o protótipo (D-08). As bibliotecas agregadoras alargam a superfície de supply chain do componente que guarda as chaves: o LiteLLM 1.82.7/1.82.8 foi publicado com código malicioso no PyPI a 24 Mar 2026.

## Opções consideradas
1. **Porta própria fina (`LLMGateway`)** com adaptadores sobre os SDK oficiais.
2. **LiteLLM** (SDK ou proxy). Muitos fornecedores, mas grande superfície de dependências e de risco.
3. **Pydantic AI** (MIT, Python ≥ 3.11). Bom tipo de abstracção, mas é mais uma camada a seguir.
4. **SDK directo sem abstracção.** Contraria a p.20.

## Decisão
- **Opção 1.** A interface `LLMGateway` tem `generate`, `stream`, `embed`, `count_tokens` e flags de capacidade por modelo.
- Mensagens, ferramentas, output estruturado e eventos de stream são canónicos.
- **Adaptadores na v1:**
  - Anthropic (SDK oficial);
  - Ollama;
  - `fake` determinístico para a CI.
- **Não se abstrai:**
  - os prompts, que são versionados por família de modelo;
  - as features específicas de cada fornecedor, expostas como dicas opcionais;
  - o ciclo do agente;
  - a política.
- Cada chamada é rastreada e custeada (`model_usage`).
- Reavaliar o Pydantic AI como implementação de adaptador depois de um spike, ou quando houver 3 ou mais fornecedores.

## Consequências
- **Positivas:** comportamento de streaming e tool calls à vista; poucas dependências; adaptadores testáveis com fixtures gravadas.
- **Negativas:** mais código a manter; as features têm de ser mapeadas à mão. O Ollama não suporta `tool_choice`, por isso padrões de ferramenta forçada não são portáveis.

## Verificação
- Testes de contrato por adaptador com fixtures gravadas.
- O fornecedor `fake` mantém a CI sem rede (AC-10).

## Fontes (verificadas a 2026-11-20)
- platform.claude.com/docs/en/about-claude/pricing
- docs.ollama.com/api/openai-compatibility
- pypi.org/project/pydantic-ai
- pypi.org/project/litellm
- infoq.com/news/2026/03/litellm-supply-chain-attack
