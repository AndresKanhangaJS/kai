#!/usr/bin/env bash
# Testes de integração do apps/api contra serviços reais (M03 E2.1: RabbitMQ).
# Stack descartável `kai-it`, sem portas publicadas, com passwords aleatórias
# em cada corrida; não toca na stack de dev. Uso: scripts/ci/integration.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

export COMPOSE_PROJECT_NAME=kai-it
# Todos os profiles da stack: sem isto, o `down` não apaga os serviços com
# profile (rabbitmq) e uma corrida reaproveitaria o volume de outra (o import
# de definições é aditivo). Um profile novo no compose entra aqui.
export COMPOSE_PROFILES=messaging
COMPOSE=(docker compose -f docker-compose.yml)

rand() { printf 'it-'; head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

cleanup() { "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "→ O RabbitMQ recusa arrancar com passwords vazias, de exemplo ou curtas"
refuses() {
  local label=$1 rc=0; shift
  # timeout: se a validação regredir, o servidor arrancaria em primeiro plano;
  # o 124 (timeout) conta como "arrancou", não como recusa.
  out=$(timeout 60 env "$@" "${COMPOSE[@]}" run --rm --no-deps -T rabbitmq 2>&1) || rc=$?
  if [ "$rc" -eq 0 ] || [ "$rc" -eq 124 ]; then
    echo "FALHA: arrancou com $label"; exit 1
  fi
  grep -q "render-definitions:" <<<"$out" || { echo "FALHA: $label falhou por outro motivo"; exit 1; }
  echo "  ✓ recusa: $label"
}
strong=$(rand)
refuses "passwords vazias" KAI_RABBITMQ_ADMIN_PASSWORD= KAI_RABBITMQ_API_PASSWORD= KAI_RABBITMQ_AI_ENGINE_PASSWORD=
refuses "valor de exemplo" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD=changeme-rabbitmq-api-xxxxxxxx KAI_RABBITMQ_AI_ENGINE_PASSWORD="$strong"
refuses "password curta" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD="$strong" KAI_RABBITMQ_AI_ENGINE_PASSWORD=curta
bad="${strong}&\"injectado"
refuses "caracteres inválidos" KAI_RABBITMQ_ADMIN_PASSWORD="$strong" KAI_RABBITMQ_API_PASSWORD="$bad" KAI_RABBITMQ_AI_ENGINE_PASSWORD="$strong"

export KAI_RABBITMQ_ADMIN_PASSWORD=$(rand)
export KAI_RABBITMQ_API_PASSWORD=$(rand)
export KAI_RABBITMQ_AI_ENGINE_PASSWORD=$(rand)

echo "→ RabbitMQ (stack kai-it)"
"${COMPOSE[@]}" up -d --wait rabbitmq

echo "→ Limites e topic permissions carregados"
ctl() { "${COMPOSE[@]}" exec -T rabbitmq rabbitmqctl -q "$@"; }
ctl list_user_limits --user kai-api | grep -q '"max-connections":20' || { echo "FALHA: limites do kai-api"; exit 1; }
ctl list_user_limits --user kai-ai-engine | grep -q '"max-channels":100' || { echo "FALHA: limites do kai-ai-engine"; exit 1; }
ctl list_vhost_limits -p /kai | grep -q '"max-connections":100' || { echo "FALHA: limites do vhost"; exit 1; }
[ "$(ctl list_topic_permissions -p /kai | grep -c 'kai\.')" -eq 2 ] || { echo "FALHA: topic permissions"; exit 1; }
[ "$(ctl list_users | grep -c '^kai-')" -eq 3 ] || { echo "FALHA: utilizadores inesperados"; exit 1; }
echo "  ✓ 3 utilizadores, limites por utilizador e por vhost, 2 topic permissions"

echo "→ Pest (tests/Integration)"
"${COMPOSE[@]}" build -q api
"${COMPOSE[@]}" run --rm --no-deps -T \
  -v "$PWD/packages/contracts:/contracts:ro" \
  -e APP_ENV=testing -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: -e BROADCAST_CONNECTION=null \
  -e RABBITMQ_HOST=rabbitmq -e KAI_CONTRACTS_DIR=/contracts \
  -e KAI_RABBITMQ_ADMIN_PASSWORD -e KAI_RABBITMQ_API_PASSWORD -e KAI_RABBITMQ_AI_ENGINE_PASSWORD \
  api vendor/bin/pest tests/Integration
