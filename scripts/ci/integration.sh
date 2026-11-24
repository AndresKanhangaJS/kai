#!/usr/bin/env bash
# Testes de integração do apps/api contra serviços reais: RabbitMQ (M03 E2.1),
# otel-lgtm (M03 E2.2) e AI Engine (M03 E3.2 e E3.4a: consumidor e inbox). Stack descartável `kai-it`, com passwords aleatórias
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
"${COMPOSE[@]}" build -q ai-engine
refuses ai-engine KAI_RABBITMQ_AI_ENGINE_PASSWORD "password vazia" KAI_RABBITMQ_AI_ENGINE_PASSWORD=
refuses ai-engine KAI_AI_ENGINE_REDIS_PASSWORD "password do Redis vazia" KAI_RABBITMQ_AI_ENGINE_PASSWORD="$strong" KAI_AI_ENGINE_REDIS_PASSWORD=
refuses ai-engine-redis ai-engine-redis: "password vazia" KAI_AI_ENGINE_REDIS_PASSWORD=
refuses ai-engine-redis ai-engine-redis: "valor de exemplo" KAI_AI_ENGINE_REDIS_PASSWORD=changeme-redis-xxxxxxxxxxxxxxxxxx
refuses ai-engine-redis ai-engine-redis: "password curta (23)" KAI_AI_ENGINE_REDIS_PASSWORD=it-aaaaaaaaaaaaaaaaaaaa
refuses ai-engine-redis ai-engine-redis: "caracteres inválidos" KAI_AI_ENGINE_REDIS_PASSWORD="$bad"
refuses otel-lgtm otel-lgtm: "password vazia" KAI_GRAFANA_ADMIN_PASSWORD=
refuses otel-lgtm otel-lgtm: "valor de exemplo" KAI_GRAFANA_ADMIN_PASSWORD=changeme-grafana-xxxxxxxxxxxxxx
refuses otel-lgtm otel-lgtm: "password curta (23)" KAI_GRAFANA_ADMIN_PASSWORD=it-aaaaaaaaaaaaaaaaaaaa
refuses otel-lgtm otel-lgtm: "caracteres inválidos" KAI_GRAFANA_ADMIN_PASSWORD="$bad"

export KAI_RABBITMQ_ADMIN_PASSWORD=$(rand)
export KAI_RABBITMQ_API_PASSWORD=$(rand)
export KAI_RABBITMQ_AI_ENGINE_PASSWORD=$(rand)
export KAI_GRAFANA_ADMIN_PASSWORD=$(rand)
export KAI_AI_ENGINE_REDIS_PASSWORD=$(rand)

echo "→ RabbitMQ, otel-lgtm, Redis da inbox e AI Engine (stack kai-it)"
"${COMPOSE[@]}" up -d --build --wait rabbitmq otel-lgtm ai-engine-redis ai-engine

echo "→ AI Engine: nenhuma porta publicada no host (ADR-0010)"
[ -z "$(docker port "$("${COMPOSE[@]}" ps -q ai-engine)")" ] || { echo "FALHA: ai-engine com portas publicadas"; exit 1; }
echo "  ✓ sem portas publicadas"

echo "→ AI Engine: contentor endurecido e isolado do MySQL e do Redis (ADR-0002)"
cid=$("${COMPOSE[@]}" ps -q ai-engine)
[ "$(docker inspect -f '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}} {{.Config.User}}' "$cid")" = "true [ALL] kai" ] \
  || { echo "FALHA: ai-engine sem read_only, cap_drop ALL ou utilizador não-root"; exit 1; }
if "${COMPOSE[@]}" exec -T ai-engine python -I -c "import pip" >/dev/null 2>&1; then echo "FALHA: pip na imagem de runtime"; exit 1; fi
# mysql e redis sobem só para provar que o ai-engine NÃO lhes chega; com `run`
# não publicam portas (não colidem com a stack de dev), e --use-aliases dá-lhes
# o nome do serviço na rede default.
"${COMPOSE[@]}" run -d --no-deps --use-aliases mysql >/dev/null
"${COMPOSE[@]}" run -d --no-deps --use-aliases redis >/dev/null
reach() { "${COMPOSE[@]}" exec -T ai-engine python -I -c "import socket,sys
try: socket.create_connection(('$1', $2), timeout=3).close(); print('open')
except OSError: print('closed')"; }
# Controlo positivo: da rede default (api), o mysql e o redis respondem.
api_reach() { "${COMPOSE[@]}" run --rm --no-deps -T api php -r "exit(@fsockopen('$1', $2, \$e, \$m, 3) ? 0 : 1);" >/dev/null 2>&1; }
for target in "mysql 3306" "redis 6379"; do
  ok=0
  # shellcheck disable=SC2086
  for _ in $(seq 1 30); do if api_reach $target; then ok=1; break; fi; sleep 3; done
  [ "$ok" = 1 ] || { echo "FALHA: controlo positivo ($target a partir do api)"; exit 1; }
done
[ "$(reach rabbitmq 5672)" = open ] || { echo "FALHA: controlo positivo (rabbitmq a partir do ai-engine)"; exit 1; }
for target in "mysql 3306" "redis 6379"; do
  # shellcheck disable=SC2086
  [ "$(reach $target)" = closed ] || { echo "FALHA: ai-engine chega a $target"; exit 1; }
done
echo "  ✓ read_only, cap_drop ALL, utilizador kai, sem pip; chega ao rabbitmq, não ao mysql nem ao redis"

echo "→ Redis da inbox: só o ai-engine, sem portas, default desligado e ACL limitada (P-020)"
rcid=$("${COMPOSE[@]}" ps -q ai-engine-redis)
[ -z "$(docker port "$rcid")" ] || { echo "FALHA: ai-engine-redis com portas publicadas"; exit 1; }
[ "$(docker inspect -f '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}}' "$rcid")" = "true [ALL]" ] \
  || { echo "FALHA: ai-engine-redis sem read_only ou cap_drop ALL"; exit 1; }
[ "$(reach ai-engine-redis 6379)" = open ] || { echo "FALHA: controlo positivo (ai-engine-redis a partir do ai-engine)"; exit 1; }
if api_reach ai-engine-redis 6379; then echo "FALHA: o api chega ao ai-engine-redis"; exit 1; fi
rcli() { "${COMPOSE[@]}" exec -T ai-engine-redis redis-cli --no-auth-warning "$@" 2>&1; }
out=$(rcli ping); grep -q NOAUTH <<<"$out" || { echo "FALHA: o Redis responde sem autenticação"; exit 1; }
out=$(rcli --user default --pass qualquer-coisa ping); grep -qiE "WRONGPASS|disabled" <<<"$out" || { echo "FALHA: utilizador default activo"; exit 1; }
as_engine() { rcli --user kai-ai-engine --pass "$KAI_AI_ENGINE_REDIS_PASSWORD" "$@"; }
[ "$(as_engine ping)" = PONG ] || { echo "FALHA: o kai-ai-engine não autentica no Redis"; exit 1; }
for cmd in "get outra:chave" "set outra:chave x" "config get maxmemory" "flushall" "scan 0" "del inbox:ai-engine:x" "acl list"; do
  # shellcheck disable=SC2086
  out=$(as_engine $cmd); grep -q NOPERM <<<"$out" || { echo "FALHA: o kai-ai-engine pode correr '$cmd'"; exit 1; }
done
# shellcheck disable=SC2016
rleaks=$("${COMPOSE[@]}" exec -T ai-engine-redis sh -c 'for p in /proc/[0-9]*; do [ "${p#/proc/}" = "$$" ] && continue; grep -qaF "$KAI_AI_ENGINE_REDIS_PASSWORD" "$p/environ" 2>/dev/null && echo "$p"; done; grep -qF "$KAI_AI_ENGINE_REDIS_PASSWORD" /tmp/kai-redis/users.acl && echo acl; true')
[ -z "$rleaks" ] || { echo "FALHA: password do Redis em claro ($rleaks)"; exit 1; }
echo "  ✓ sem portas, read_only, só o ai-engine lhe chega; NOAUTH sem password, default desligado"
echo "  ✓ kai-ai-engine só com GET/SET/PING em inbox:ai-engine:*; password só como hash no ACL"

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

pest() {
  "${COMPOSE[@]}" run --rm --no-deps -T \
    -v "$PWD/packages/contracts:/contracts:ro" \
    -e APP_ENV=testing -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: -e BROADCAST_CONNECTION=null \
    -e RABBITMQ_HOST=rabbitmq -e OTEL_LGTM_HOST=otel-lgtm -e AI_ENGINE_HOST=ai-engine -e KAI_CONTRACTS_DIR=/contracts \
    -e KAI_RABBITMQ_ADMIN_PASSWORD -e KAI_RABBITMQ_API_PASSWORD -e KAI_RABBITMQ_AI_ENGINE_PASSWORD \
    -e KAI_GRAFANA_ADMIN_PASSWORD \
    api vendor/bin/pest "$@"
}
"${COMPOSE[@]}" build -q api
# Os testes de topologia consomem a ai-engine.commands como kai-ai-engine: com o
# consumidor ligado, competiam pelas mensagens. Correm com o ai-engine parado.
echo "→ Pest: topologia do RabbitMQ e otel-lgtm (ai-engine parado)"
"${COMPOSE[@]}" stop ai-engine >/dev/null 2>&1
pest tests/Integration/RabbitMqTopologyTest.php tests/Integration/OtelLgtmTest.php
"${COMPOSE[@]}" up -d --wait ai-engine
echo "→ Pest: AI Engine real"
pest tests/Integration/AiEngineHealthTest.php

echo "→ AI Engine: fluxo do turno contra o broker real (AC-004-02, 04, 05, 06, 07, 09)"
docker build -q --target dev --build-context contracts=packages/contracts -t kai-ai-engine-it apps/ai-engine >/dev/null
turn_flow() {
  docker run --rm --network kai-it_messaging --read-only --tmpfs /tmp \
    -v "$PWD/packages/contracts:/contracts:ro" -e KAI_CONTRACTS_DIR=/contracts \
    -e KAI_IT_RABBITMQ_HOST=rabbitmq -e KAI_IT_SCENARIO="$1" \
    -e KAI_RABBITMQ_API_PASSWORD -e KAI_RABBITMQ_ADMIN_PASSWORD \
    --entrypoint pytest kai-ai-engine-it -p no:cacheprovider -q tests/integration
}
# with_fake <cenário> VAR=valor...: recria o ai-engine com o fake configurado e corre o cenário.
with_fake() {
  local name=$1; shift
  env "$@" "${COMPOSE[@]}" up -d --wait --force-recreate ai-engine >/dev/null 2>&1 \
    || { echo "FALHA: ai-engine não arrancou no cenário $name"; exit 1; }
  echo "  cenário $name"
  turn_flow "$name"
}
turn_flow base
with_fake budget KAI_FAKE_USD_PER_MTOK=1000000
with_fake retry KAI_FAKE_FAIL_BEFORE_FIRST_DELTA=2
with_fake slow KAI_FAKE_DELAY_PER_DELTA=0.5 KAI_FAKE_WORDS_PER_DELTA=1
"${COMPOSE[@]}" up -d --wait --force-recreate ai-engine >/dev/null 2>&1

echo "→ AI Engine: a readiness acompanha o RabbitMQ (AC-004-01, NFR-027)"
ready() { "${COMPOSE[@]}" exec -T ai-engine python -I -c "import urllib.request,urllib.error
try: print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).status)
except urllib.error.HTTPError as e: print(e.code)"; }
wait_ready() {
  local want=$1
  for _ in $(seq 1 60); do [ "$(ready)" = "$want" ] && return 0; sleep 1; done
  echo "FALHA: /health/ready não chegou a $want"; exit 1
}
"${COMPOSE[@]}" stop rabbitmq >/dev/null 2>&1
wait_ready 503
echo "  ✓ 503 com o RabbitMQ parado"
"${COMPOSE[@]}" start rabbitmq >/dev/null 2>&1
wait_ready 200
echo "  ✓ 200 depois de o RabbitMQ voltar (reconexão, com o consumidor restaurado)"
turn_flow base >/dev/null || { echo "FALHA: o consumidor não voltou a processar turnos depois da reconexão"; exit 1; }
echo "  ✓ processa turnos depois da reconexão"
"${COMPOSE[@]}" stop ai-engine-redis >/dev/null 2>&1
wait_ready 503
echo "  ✓ 503 com o Redis da inbox parado"
"${COMPOSE[@]}" start ai-engine-redis >/dev/null 2>&1
wait_ready 200
echo "  ✓ 200 depois de o Redis voltar"

echo "→ AI Engine: a password nunca aparece nos logs"
# Os logs vão primeiro para uma variável: com pipefail, um `grep -q` que encontra
# e sai cedo faz o `logs` levar SIGPIPE, e a condição daria falso (fuga não detectada).
engine_logs=$("${COMPOSE[@]}" logs ai-engine ai-engine-redis 2>&1)
for pw in "$KAI_RABBITMQ_AI_ENGINE_PASSWORD" "$KAI_AI_ENGINE_REDIS_PASSWORD"; do
  if grep -qF "$pw" <<<"$engine_logs"; then
    echo "FALHA: password nos logs do ai-engine ou do Redis (após reconexão)"; exit 1
  fi
done
wrong=$(rand)
out=$(timeout 15 env KAI_RABBITMQ_AI_ENGINE_PASSWORD="$wrong" "${COMPOSE[@]}" run --rm --no-deps -T ai-engine 2>&1) || true
grep -q "rabbitmq_connect_failed" <<<"$out" || { echo "FALHA: a password errada não foi recusada pelo broker"; exit 1; }
if grep -qF "$wrong" <<<"$out"; then echo "FALHA: password errada nos logs do ai-engine"; exit 1; fi
echo "  ✓ nem após a reconexão nem com uma password recusada (ACCESS_REFUSED)"
