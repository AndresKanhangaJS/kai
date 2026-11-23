---
paths:
  - "apps/ai-engine/**"
---
# AI Engine (`apps/ai-engine`): Python 3.14 + FastAPI

## Fronteiras
- Sem estado de negócio autoritativo: o Python propõe e reporta, o Laravel decide e persiste (ADR-0002).
- Nenhuma ferramenta corre sem *execution grant* válido: assinatura (chave pública), `exp`, `jti` ainda não usado, hash dos args.
- O Context Builder recebe o snapshot de permissões do Laravel; o retrieval exige filtro `user_id` e re-verifica os hits.

## LLM (ADR-0006)
- Chamadas só através da porta `LLMGateway`; nunca uses o SDK de um fornecedor directamente fora do adaptador.
- Cada chamada tem `max_tokens`, timeout e orçamento da missão, e regista em `model_usage` (modelo, versão do prompt, tokens, custo, latência, trace_id).
- Os prompts são ficheiros versionados por família de modelo; conteúdo externo vai em blocos de dados delimitados, com origem.
- Output estruturado é validado com Pydantic: 1 tentativa de reparação, depois falha. Não há reparação silenciosa.
- Existe sempre um adaptador `fake` determinístico para testes sem rede.

## Mensagens
- Consumidores idempotentes (inbox); retry com backoff e jitter; DLQ.
- Extrai e propaga `traceparent` dos headers AMQP.
- Deltas de streaming são efémeros (Reverb) e não passam pelo RabbitMQ.

## Qualidade
- Tipagem completa (mypy strict), pytest, Ruff.
- Avaliações em `apps/ai-engine/evals/`, com datasets versionados (skill `kai-eval`).
- Executa sempre com `python -I` quando processar ficheiros não confiáveis; nunca uses `eval`, `exec` nem `pickle` sobre input externo.
- Comandos: `scripts/ci/ai-engine.sh` (ruff, `ruff format --check`, mypy strict, pytest, sem rede) e `scripts/ci/integration.sh` (serviço real). Locks: `scripts/dev/ai-engine-lock.sh <data limite>`; dependências novas pedem a aprovação do owner (P-021).
