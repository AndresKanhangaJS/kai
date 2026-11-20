# Observabilidade (global)

Stack inicial: OpenTelemetry + `grafana/otel-lgtm` (M03); stack separada (Prometheus, Loki, Tempo, Grafana) no M10. Skill: `kai-observability`.

## Propagação de trace
- Cliente → Laravel: aceita e propaga `traceparent` (W3C Trace Context).
- Laravel → RabbitMQ: guarda `traceparent`/`tracestate` na linha do outbox quando a escreves; o relay põe-nos nos headers AMQP e cria um span PRODUCER.
- RabbitMQ → Python: extrai o contexto dos headers e cria um span CONSUMER, filho do span de origem, para comandos de mensagem única.
- Python → LLM e ferramentas: um span por chamada; o evento de retorno leva um novo `traceparent`.
- Fixa a versão das semconv de messaging, que ainda estão em estado *Development*.

## Nomes
- Spans: `<verbo> <recurso>` (ex.: `publish kai.commands`, `llm.generate`, `tool.execute github.repo.read`).
- Métricas: prefixo `kai_`, unidades no nome, snake_case. Por exemplo:
  - `kai_http_server_duration_seconds`
  - `kai_llm_tokens_total{direction}`
  - `kai_llm_cost_usd_total`
  - `kai_tool_executions_total{tool,outcome}`
  - `kai_mission_outcomes_total{state}`
  - `kai_queue_dlq_messages`
- Labels com cardinalidade baixa: nunca `user_id`, `mission_id` nem texto livre nas métricas (vão nos traces e nos logs).

## Logs
- JSON estruturado com `trace_id`, `span_id`, `service`, `level`, `event`.
- Nunca prompts, respostas, conteúdo de documentos, emails, tokens, cookies ou credenciais. Usa IDs e hashes.
- Erros: classe, código e mensagem segura; o stack trace só em desenvolvimento.

## Mínimos por funcionalidade
- RED (taxa, erros, duração) por rota HTTP e por consumidor.
- Profundidade de fila e DLQ; latência, tokens e custo do LLM; resultados das missões.
- Health checks `/health/live` e `/health/ready` em todos os serviços.
