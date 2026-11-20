# Testes (global)

## Pirâmide
- **Unitários (muitos):** regras de domínio, política (níveis 1–6, aprovações), máquina de estados da missão, validação de schemas.
- **Integração:** BD (MySQL real em contentor), RabbitMQ (outbox → relay → consumidor), Redis, Qdrant.
- **Contrato:** exemplos dos schemas validados pelos dois lados (`packages/contracts`).
- **Arquitectura:** fronteiras entre módulos; nenhum caminho até um adaptador de ferramenta sem grant (NFR-001).
- **E2E (poucos):** os critérios de aceitação do MVP (AC-01 a AC-10), em Playwright.

## Regras
- Um critério de aceitação vira pelo menos um teste com o mesmo identificador no nome (`AC-05`).
- Escreve os testes de segurança como casos negativos explícitos: sem grant, grant expirado, args alterados, `user_id` de outro dono, nível 6.
- Os testes não usam rede nem chaves reais: LLM `fake`, fixtures gravadas, dados sintéticos.
- Um teste instável (*flaky*) corrige-se ou isola-se com uma issue; nunca se ignora em silêncio.
- Nunca enfraqueças nem apagues um teste para o fazer passar; se o teste estiver errado, explica porquê.

## Agentes e LLM: avaliações, não impressões
- O comportamento de agentes mede-se com avaliações versionadas (skill `kai-eval`), nunca com demos subjectivas (PDF p.19).
- Datasets imutáveis por versão (`evals/datasets/<suite>/<semver>/`), com o hash no manifest.
- Métricas: Task Success, Tool Success, Groundedness, Retrieval Quality, Cost per Task, Latency.
- Os PRs correm testes determinísticos com o fake. As alterações a prompts, modelos ou retrieval correm a suite live com limiares.
- Uma regressão acima do limiar bloqueia a release (NFR-020).

## Evidência
- Afirmar "os testes passam" exige o comando executado e o output relevante no relatório ou no PR.
