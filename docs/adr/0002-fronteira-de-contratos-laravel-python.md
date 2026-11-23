# ADR-0002: Fronteira de contratos Laravel ↔ Python

- **Estado:** Aceite
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.4, p.7–9, p.19–20; ADR-0001, 0003, 0010, 0013; `docs/product/analysis.md` §5

## Contexto
- O PDF chama "KAI Core" ao núcleo que compreende, planeia e coordena [C p.4, p.9], mas coloca utilizadores, conversas, agentes, ferramentas, missões e auditoria no Core Platform Laravel [C p.7]. Não diz quem é dono do quê (A-02, A-03, A-04).
- Pede contratos definidos [C p.5, p.9] e publicação de OpenAPI e de contratos de eventos [C p.19].
- Pergunta como serão versionados [C p.20].

## Opções consideradas
1. **Laravel como sistema de registo e PDP; Python cognitivo e sem estado autoritativo.** Um só dono de cada estado e uma fronteira de segurança clara.
2. **Python dono das missões e do planeamento.** Menos idas e voltas, mas duas fontes de verdade e um PDP no componente mais exposto a prompt injection.
3. **BD partilhada entre os dois.** Simples no início, mas acoplamento forte e sem fronteira.

## Decisão
- **Opção 1.** O Laravel é o único escritor de missões, aprovações, auditoria e memórias.
- O Python propõe e reporta por eventos e executa ferramentas só com *execution grants* (ADR-0004).
- **Síncrono** (OpenAPI 3.1), só onde é preciso resposta imediata: autorização de ferramentas, health e retrieval interactivo.
- **Assíncrono** (RabbitMQ; AsyncAPI 3.x + JSON Schema) para o que é longo ou muda estado.
- Contratos em `packages/contracts`.
- Versionamento: a major vai no nome do tipo; dentro de uma major só há alterações aditivas; uma alteração incompatível cria uma nova major, publicada em paralelo durante pelo menos um milestone.
- Não há tabelas partilhadas. O dono de `document_chunks` fica em aberto (P-014).

## Consequências
- **Positivas:** deploy e testes independentes; cada estado tem um só dono; fronteira auditável.
- **Negativas:** DTOs duplicados (PHP e Pydantic); testes de contrato para manter; mais uma ida e volta por ferramenta.

## Verificação
- Testes de contrato na CI, dos dois lados (M02).
- Teste de arquitectura que impede o Python de escrever em tabelas do Laravel.
