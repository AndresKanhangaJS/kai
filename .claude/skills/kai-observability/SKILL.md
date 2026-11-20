---
name: kai-observability
description: Instrumenta código do KAI com OpenTelemetry. Cobre spans, métricas e logs correlacionados, a propagação de trace context por HTTP e por filas RabbitMQ (outbox → AMQP → consumidor Python), e os dashboards e alertas mínimos. Usa ao criar endpoints, consumidores, chamadas LLM ou ferramentas, ou quando o owner disser "instrumenta", "trace", "métricas", "dashboard", "alerta", "porque é que isto está lento?".
---
# kai-observability: instrumentação OpenTelemetry

Regras de nomes e conteúdos: `.claude/rules/observability.md`. Stack: `grafana/otel-lgtm` no M03 (ADR-0011); stack separada no M10.

## Procedimento por funcionalidade
1. **Inventário:** que operações a funcionalidade adiciona (rota HTTP, publicação, consumo, chamada LLM, ferramenta, job)?
2. **Spans:**
   - um por operação, com o nome `<verbo> <recurso>`;
   - atributos semconv (HTTP, messaging, `gen_ai.*` se estiver estável na versão fixada);
   - atributos KAI com IDs: `kai.mission_id`, `kai.tool`, `kai.operation_level`, `kai.agent_version`;
   - nunca conteúdo.
3. **Propagação:**
   - HTTP: `traceparent` de entrada e saída.
   - Outbox: guarda `traceparent` e `tracestate` na linha quando é escrita.
   - Relay: span PRODUCER; headers AMQP `traceparent` e `tracestate`.
   - Consumidor Python: extrai os headers, cria um span CONSUMER (filho para comando único, link para lotes).
   - Testa a propagação com um teste de integração que verifica que o `trace_id` é o mesmo nos dois lados.
4. **Métricas:**
   - RED por rota e consumidor;
   - `kai_llm_tokens_total`, `kai_llm_cost_usd_total`, `kai_tool_executions_total{tool,outcome}`, `kai_mission_outcomes_total{state}`, `kai_queue_dlq_messages`;
   - labels de baixa cardinalidade.
5. **Logs:**
   - JSON com `trace_id` e `span_id` injectados automaticamente;
   - eventos nomeados (`mission.state_changed`, `tool.denied`);
   - sem PII nem conteúdo.
6. **Erros:** marca o span com estado de erro e regista a classe ou o código; não repitas a mensagem com dados sensíveis.
7. **Health:** `/health/live` (processo) e `/health/ready` (dependências), usados no Compose e na monitorização.

## Dashboards mínimos (M03; versionados como ficheiros quando existirem)
- **Visão geral:** taxa, erros e latência p50/p95 por serviço.
- **IA:** TTFT, latência por tipo de tarefa, tokens e custo por dia e por missão, falhas do LLM.
- **Filas:** profundidade, consumidores, rejeições, DLQ.
- **Missões:** resultados por estado, aprovações pendentes, recusas de política.

## Alertas mínimos
- DLQ > 0 durante 5 min.
- Taxa de erro > 5 % durante 10 min.
- Custo diário > 80 % do tecto (P-002).
- Serviço não *ready* durante 2 min.
- Falhas de verificação de grant (possível ataque) > 0.

## Verificação
- Um pedido E2E produz um único trace visível de React → Laravel → RabbitMQ → Python → LLM (AC-08).
- Grep aos logs de teste sem conteúdo sensível: procura um marcador sintético injectado no input; tem de dar zero ocorrências.
