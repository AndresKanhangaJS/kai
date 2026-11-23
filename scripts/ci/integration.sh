#!/usr/bin/env bash
# Testes de integração do apps/api contra serviços reais: RabbitMQ (M03 E2.1)
# e otel-lgtm (M03 E2.2). Stack descartável `kai-it`, com passwords aleatórias
# em cada corrida; não toca na stack de dev. Uso: scripts/ci/integration.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

export COMPOSE_PROJECT_NAME=kai-it
# Todos os profiles da stack: sem isto, o `down` não apaga os serviços com
# profile e uma corrida reaproveitaria o volume de outra (o import de
# definições do RabbitMQ é aditivo). Um profile novo no compose entra aqui.
export COMPOSE_PROFILES=messaging,observability
# Porta efémera para o Grafana: a stack de dev pode estar ligada com a 3000.
export KAI_GRAFANA_HOST_PORT=
COMPOSE=(docker compose -f docker-compose.yml)

rand() { printf 'it-'; head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

cleanup() { "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

# refuses <serviço> <prefixo da mensagem de recusa> <descrição> VAR=valor...
refuses() {
  local service=$1 prefix=$2 label=$3 rc=0; shift 3
  # timeout: se a validação regredir, o serviço arrancaria em primeiro plano;
  # o 124 (timeout) conta como "arrancou", não como recusa.
  out=$(timeout 60 env "$@" "${COMPOSE[@]}" run --rm --no-deps -T "$service" 2>&1) || rc=$?
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
    echo "FALHA: $service arrancou com $label"; exit 1
  fi
  grep -q "$prefix" <<<"$out" || { echo "FALHA: $service com $label falhou por outro motivo"; exit 1; }
  echo "  ✓ $service recusa: $label"
}
strong=$(rand)
bad="${strong}&\"injectado"

echo "→ Os serviços recusam arrancar com passwords vazias, de exemplo, curtas ou inválidas"
refuses rabbitmq render-definitions: "passwords vazias" KAI_RABBITMQ_ADMIN_PASSWORD= KAI_RABBITMQ_API_PASSWORD= KAI_RABBITMQ_AI_ENGINE_PASSWORD=
refuses rabbitmq render-definitions: "valor de exemplo" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD=changeme-rabbitmq-api-xxxxxxxx KAI_RABBITMQ_AI_ENGINE_PASSWORD="$strong"
refuses rabbitmq render-definitions: "password curta" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD="$strong" KAI_RABBITMQ_AI_ENGINE_PASSWORD=curta
refuses rabbitmq render-definitions: "caracteres inválidos" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD="$bad" KAI_RABBITMQ_AI_ENGINE_PASSWORD="$strong"
refuses otel-lgtm otel-lgtm: "password vazia" KAI_GRAFANA_ADMIN_PASSWORD=
refuses otel-lgtm otel-lgtm: "valor de exemplo" KAI_GRAFANA_ADMIN_PASSWORD=changeme-grafana-xxxxxxxxxxxxxx
refuses otel-lgtm otel-lgtm: "password curta (23)" KAI_GRAFANA_ADMIN_PASSWORD=it-aaaaaaaaaaaaaaaaaaaa
refuses otel-lgtm otel-lgtm: "caracteres inválidos" KAI_GRAFANA_ADMIN_PASSWORD="$bad"

export KAI_RABBITMQ_ADMIN_PASSWORD=$(rand)
export KAI_RABBITMQ_API_PASSWORD=$(rand)
export KAI_RABBITMQ_AI_ENGINE_PASSWORD=$(rand)
export KAI_GRAFANA_ADMIN_PASSWORD=$(rand)

echo "→ RabbitMQ e otel-lgtm (stack kai-it)"
"${COMPOSE[@]}" up -d --wait rabbitmq otel-lgtm

echo "→ Limites e topic permissions do RabbitMQ carregados"
ctl() { "${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl -q "$@"; }
ctl list_user_limits --user kai-api | grep -q '"max-connections":20' || { echo "FALHA: limites do kai-api"; exit 1; }
ctl list_user_limits --user kai-ai-engine | grep -q '"max-channels":100' || { echo "FALHA: limites do kai-ai-engine"; exit 1; }
ctl list_vhost_limits -p /kai | grep -q '"max-connections":100' || { echo "FALHA: limites do vhost"; exit 1; }
[ "$(ctl list_topic_permissions -p /kai | grep -c 'kai\.')" -eq 2 ] || { echo "FALHA: topic permissions"; exit 1; }
[ "$(ctl list_users | grep -c '^kai-')" -eq 3 ] || { echo "FALHA: utilizadores inesperados"; exit 1; }
echo "  ✓ 3 utilizadores, limites por utilizador e por vhost, 2 topic permissions"

echo "→ otel-lgtm: só o Grafana publicado no host"
for port in 3100 3200 4040 4317 4318 9090 13133; do
  if "${COMPOSE[@]}" port otel-lgtm "$port" >/dev/null 2>&1; then echo "FALHA: porta $port publicada"; exit 1; fi
done
"${COMPOSE[@]}" port otel-lgtm 3000 | grep -q '^127\.0\.0\.1:' || { echo "FALHA: Grafana fora de 127.0.0.1"; exit 1; }
echo "  ✓ só 127.0.0.1 → 3000"
# A password vai num ficheiro 0400 lido pelo Grafana ($__file{}): nenhum serviço
# a pode ter no ambiente. O shell deste exec herda-a do Config.Env e é excluído.
# shellcheck disable=SC2016
leaks=$("${COMPOSE[@]}" exec -T otel-lgtm sh -c 'for p in /proc/[0-9]*; do [ "${p#/proc/}" = "$$" ] && continue; grep -qaF "$KAI_GRAFANA_ADMIN_PASSWORD" "$p/environ" 2>/dev/null && echo "$p"; done; true')
[ -z "$leaks" ] || { echo "FALHA: password do Grafana no ambiente de processos"; exit 1; }
echo "  ✓ password do Grafana fora do ambiente dos serviços"

echo "→ Pest (tests/Integration)"
"${COMPOSE[@]}" build -q api
"${COMPOSE[@]}" run --rm --no-deps -T \
  -v "$PWD/packages/contracts:/contracts:ro" \
  -e APP_ENV=testing -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: -e BROADCAST_CONNECTION=null \
  -e RABBITMQ_HOST=rabbitmq -e OTEL_LGTM_HOST=otel-lgtm -e KAI_CONTRACTS_DIR=/contracts \
  -e KAI_RABBITMQ_ADMIN_PASSWORD -e KAI_RABBITMQ_API_PASSWORD -e KAI_RABBITMQ_AI_ENGINE_PASSWORD \
  -e KAI_GRAFANA_ADMIN_PASSWORD \
  api vendor/bin/pest tests/Integration
