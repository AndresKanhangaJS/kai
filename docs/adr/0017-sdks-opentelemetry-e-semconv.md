# ADR-0017: SDKs OpenTelemetry com instrumentação manual e semconv 1.44.0 fixada

- **Estado:** Proposto
- **Data:** 2026-11-23
- **Decisores:** owner
- **Relacionados:** P-019; NFR-002; ADR-0016; `.claude/rules/observability.md`; M03 E1.3, E2.2, E7.1

## Contexto
- [C observability.md] O trace ponta a ponta é React → Laravel → RabbitMQ → Python → LLM, com o `traceparent` guardado no outbox e passado nos headers AMQP. A versão das semconv de messaging tem de estar fixada, porque ainda estão em *Development*.
- [C, Packagist, PyPI e PECL, 2026-11-23; versões com pelo menos 2 semanas]:

| Lado | Pacote | Versão (data) | Licença |
|---|---|---|---|
| PHP | `open-telemetry/api` / `sdk` / `exporter-otlp` | 1.11.0 (11-05) / 1.16.1 (11-06) / 1.5.0 (11-05) | Apache-2.0 |
| PHP | `open-telemetry/opentelemetry-auto-laravel` | 1.10.0 (10-12) | Apache-2.0; só funciona com a extensão PECL `opentelemetry` 1.5.0 (11-09, no limite das 2 semanas) |
| Python | `opentelemetry-api` / `sdk` / `exporter-otlp-proto-http` | 1.45.2 (10-29) | Apache-2.0 |
| Python | `opentelemetry-instrumentation-fastapi` / `-aio-pika` | 0.66b2 (10-29), **beta** | Apache-2.0 |

- [C, lido nos pacotes] O `opentelemetry-semantic-conventions` 0.66b2 (exigido pelo SDK 1.45.2) declara a schema 1.44.0 e tem os atributos de messaging em `_incubating`. O `open-telemetry/sem-conv` PHP (1.45.0) declara a schema 1.32.0 no código. **As duas pontas não coincidem.**
- [C] O SDK PHP traz dois *plugins* do Composer (`php-http/discovery` e `tbachert/spi`), que correm código no `composer install`. Traz também `google/protobuf` e `nyholm/psr7-server`.

## Opções consideradas
1. **Instrumentação manual nas duas pontas, com os nomes de atributos de messaging definidos pelo KAI** (fixados na semconv 1.44.0). São poucos spans no M03: HTTP, outbox, relay, consumidor e `llm.generate`. Controlo total, menos dependências.
2. **Auto-instrumentação no Laravel (`auto-laravel` mais a extensão PECL).** Spans HTTP, BD e cache sem código, mas a extensão C entra na imagem, é muito recente e gera spans com cardinalidade e conteúdo por rever.
3. **Instrumentação contrib no Python** (FastAPI e aio-pika) **em vez de spans manuais no consumidor.** Poupa código, mas os pacotes estão em beta e a injecção de contexto do aio-pika duplica a que o envelope já leva (`traceparent`).

## Decisão
- **PHP:** `open-telemetry/api` 1.11.0, `sdk` 1.16.1 e `exporter-otlp` 1.5.0 (OTLP/HTTP), com instrumentação manual: um middleware HTTP e spans do outbox, do relay e do consumidor. Sem auto-instrumentação nem a extensão PECL no M03.
- **Python:** `opentelemetry-api`, `sdk` e `exporter-otlp-proto-http` 1.45.2, mais `opentelemetry-instrumentation-fastapi` 0.66b2 (só HTTP, de baixo risco). O consumidor AMQP cria spans CONSUMER à mão, a partir do `traceparent` do envelope (SPEC-003), sem o `-aio-pika`.
- **Semconv fixada na 1.44.0** (schema URL em todos os *tracers*). Os nomes de messaging usados pelo KAI ficam numa constante própria em cada lado (`messaging.system`, `messaging.destination.name`, `messaging.operation.type`, `messaging.message.id`), com um teste que os compara com a lista da spec.
- **Plugins do Composer:** só se autoriza o `tbachert/spi`, e só se o SDK precisar dele (por confirmar na E7.1). O `php-http/discovery` fica bloqueado em `allow-plugins` e o exporter é construído explicitamente.

## Consequências
- **Positivas:** menos dependências e nenhuma extensão C nova; os spans e os atributos são revistos para não levarem conteúdo (observability.md); o mesmo modelo nas duas linguagens.
- **Negativas / custos:** mais código de instrumentação; spans de BD e cache no Laravel só quando houver necessidade medida; actualizar a semconv passa a ser uma tarefa explícita.
- **Riscos e mitigação:** a semconv de messaging muda → os nomes estão fixados e testados; um pacote beta no FastAPI → versão exacta com hash, e é substituível por um middleware próprio.

## Verificação
- E2.2: um span de teste chega ao `otel-lgtm` pelo OTLP/HTTP (4318).
- E7.1: um único trace ponta a ponta no Tempo; um teste confirma que nenhum span tem conteúdo de mensagens.
- `composer.json` com `allow-plugins` explícito; lockfiles com hashes.

## Fontes
- Packagist (`open-telemetry/*`), PyPI (`opentelemetry-*`) e PECL (`opentelemetry`): versões, datas, licenças e `require`, consultados a 2026-11-23. Schema URLs lidas dos pacotes `opentelemetry-semantic-conventions` 0.66b2 e `open-telemetry/sem-conv` 1.45.0.
