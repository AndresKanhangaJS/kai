#!/usr/bin/env bash
# Spike M03 E1.1 (ADR-0009): Python publica deltas no Reverb e um cliente
# WebSocket recebe-os num canal privado. Exige a stack de dev a correr
# (docker compose up -d). Uso: spikes/m03-reverb/run.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

COMPOSE=(docker compose -f docker-compose.yml -f spikes/m03-reverb/compose.spike.yml --profile spike)
SUB=kai-spike-sub

cleanup() { docker rm -f "$SUB" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "→ subscritor (negativos e subscrição válida)"
"${COMPOSE[@]}" run -d --name "$SUB" --no-deps spike-sub >/dev/null
for _ in $(seq 1 60); do
  if docker logs "$SUB" 2>&1 | grep -qE '^(READY|FALHA)'; then break; fi
  sleep 0.5
done
docker logs "$SUB" 2>&1 | grep -E '^(subscricao|ligacao|client-event|READY|FALHA)'
docker logs "$SUB" 2>&1 | grep -q '^READY' || exit 1

echo "→ publicador Python"
"${COMPOSE[@]}" run --rm --no-deps -T spike-pub

echo "→ resultado"
status=$(docker wait "$SUB")
docker logs "$SUB" 2>&1 | grep -E '^(recebidos|OK|FALHA)'
exit "$status"
