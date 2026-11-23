#!/usr/bin/env bash
# SÓ O OWNER corre este script, e sempre com o output redireccionado para o
# ficheiro de ambiente: nunca através de um agente (as passwords entrariam no
# transcript) nem com o output no terminal.
#
# Gera passwords aleatórias para o RabbitMQ de dev e imprime-as no formato do
# ficheiro de ambiente da raiz do repositório. Não escreve em ficheiro
# nenhum: o owner redirecciona o output para esse ficheiro (ver
# docs/engineering/rabbitmq.md) e recria o contentor:
#   docker compose --profile messaging up -d --force-recreate rabbitmq
set -euo pipefail
gen() { head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
for name in ADMIN API AI_ENGINE; do
  printf 'KAI_RABBITMQ_%s_PASSWORD=%s\n' "$name" "$(gen)"
done
