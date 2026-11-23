# Observabilidade em dev: `grafana/otel-lgtm`

Decisões: [ADR-0017](../adr/0017-sdks-opentelemetry-e-semconv.md) (SDKs e semconv). Regras: [`.claude/rules/observability.md`](../../.claude/rules/observability.md). Entrou no M03 E2.2. Os dashboards e alertas mínimos ficam para a E7.2; a stack separada (Prometheus, Loki, Tempo, Grafana), para o M10.

## O que é

Um único contentor só para dev, com o colector OpenTelemetry, o Tempo (traces), o Loki (logs), o Prometheus (métricas), o Pyroscope e o Grafana.

- **Imagem:** `grafana/otel-lgtm:0.40.0`, fixada por digest no `docker-compose.yml` (publicada a 2026-11-06).
- **Telemetria efémera:** não há volume. Um `down`, ou recriar o contentor, apaga tudo.

## Arrancar

O Grafana **recusa arrancar** sem uma password de admin forte: vazia, com o valor de exemplo (`changeme…`), com menos de 24 caracteres ou com caracteres fora de `[A-Za-z0-9._-]`. A variável é `KAI_GRAFANA_ADMIN_PASSWORD` e é gerada pelo mesmo script do RabbitMQ:

```bash
scripts/dev/passwords.sh   # imprime as passwords do RabbitMQ e do Grafana
```

**Só o owner corre o script**, com o output redireccionado para o ficheiro de ambiente da raiz do repositório, e nunca através de um agente (ver [`rabbitmq.md`](rabbitmq.md#arrancar-em-dev)). Depois:

```bash
docker compose --profile observability up -d otel-lgtm
```

O serviço está no *profile* `observability`: um `docker compose up` sem profile não o arranca, para a AC-01 continuar a funcionar sem passwords.

## Endurecimento (`infra/otel-lgtm/start.sh`)

A imagem é um "tudo-em-um" de demonstração. O `start.sh` corre antes do entrypoint dela e muda as predefinições:

| Predefinição da imagem | No KAI |
|---|---|
| Grafana anónimo com papel **Admin** | Desligado; admin com password obrigatória (testado) |
| Descarrega o `grafana-llm-app` e outros plugins da internet no arranque | `GF_PLUGINS_PREINSTALL_DISABLED=true` (testado na configuração efectiva) |
| Estatísticas de uso para `stats.grafana.org` no Grafana, no Loki, no Tempo e no Pyroscope | Desligadas nos quatro (`GF_ANALYTICS_*`, `-reporting.enabled=false`, `-usage-stats.enabled=false`; testado na configuração efectiva de cada um) |
| Verificação de actualizações, feed de notícias, snapshots externos (`snapshots.raintank.io`), Gravatar | Desligados (testado) |
| Grafana e APIs em `0.0.0.0`, publicados no host | Só o Grafana é publicado, em `127.0.0.1:3000` (testado: as outras portas não são publicadas) |
| Na rede de toda a stack | Rede própria `telemetry`, onde só está o `api` (o único emissor previsto) |

**A password do admin** não fica no ambiente de nenhum serviço (testado). O script grava-a num ficheiro 0400 dentro do contentor e o Grafana lê-a com `$__file{}`; os outros processos só herdam o caminho. Continua visível no `docker inspect` e no `docker compose config` (vem do `environment` do Compose): **um agente nunca corre estes comandos sobre este serviço**.

O endurecimento depende de o `/otel-lgtm/run-grafana.sh` da imagem só definir os `GF_*` que ainda não existam. **Revê-o a cada mudança de digest**; os testes de configuração efectiva apanham uma regressão.

## Endpoints, a partir de outros contentores da stack

| Porta | O quê |
|---|---|
| `otel-lgtm:4317` | OTLP/gRPC |
| `otel-lgtm:4318` | OTLP/HTTP (`/v1/traces`, `/v1/metrics`, `/v1/logs`) |
| `otel-lgtm:3000` | Grafana (no host: `http://127.0.0.1:3000`, utilizador `admin`) |

**Risco aceite em dev [C: aceite pelo owner a 2026-11-23]:** quem está na rede `telemetry` (hoje só o `api`) chega sem autenticação às APIs de consulta do Tempo (3200), do Loki (3100), do Prometheus (9090) e do Pyroscope (4040), e escreve sem autenticação por OTLP (4317/4318), pelo push do Loki e pelo remote-write do Prometheus. Pode, portanto, ler IDs e forjar ou inundar telemetria. A imagem não protege estas APIs. O risco é aceitável em dev porque a telemetria leva apenas IDs e hashes, nunca conteúdo (`observability.md`), e porque a telemetria não é a auditoria (que vive no MySQL, append-only). Nenhuma destas portas é publicada no host. **Nenhuma sandbox de ferramentas pode entrar na rede `telemetry`.** Em produção (M10), a stack é outra e tem autenticação.

## Testes

`scripts/ci/integration.sh` (job `integration` da CI), numa stack descartável `kai-it`:
- a recusa de arranque com a password vazia, de exemplo, com 23 caracteres ou com caracteres inválidos;
- só a 3000 publicada no host, em `127.0.0.1`; a password fora do ambiente de todos os serviços;
- um span OTLP/HTTP sintético aparece no Tempo;
- o Grafana responde 401 sem credenciais e com `admin/admin`, e 200 com a password do ambiente;
- a configuração efectiva do Grafana tem desligados o preinstall de plugins, o acesso anónimo, o proxy e o JWT de autenticação, as estatísticas, as verificações de actualizações, os snapshots externos e o Gravatar;
- a configuração efectiva do Loki, do Tempo e do Pyroscope tem as estatísticas de uso desligadas.

Quatro defeitos injectados foram apanhados: reactivar o acesso anónimo, o preinstall, as estatísticas do Tempo, e pôr a password no ambiente.
