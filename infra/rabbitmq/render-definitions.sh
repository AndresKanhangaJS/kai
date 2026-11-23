#!/bin/sh
# Gera as definições do RabbitMQ a partir do template, com as passwords do
# ambiente, e arranca o servidor. Recusa arrancar sem passwords fortes:
# nada de valores por omissão (revisão de segurança da E2.1, achado 1). Gera
# passwords com scripts/dev/rabbitmq-passwords.sh. As passwords nunca vão para
# o argv (o awk lê-as do ENVIRON) nem para os logs; o ficheiro gerado fica só
# dentro do contentor, com modo 600, e as variáveis saem do ambiente antes de
# o servidor arrancar.
set -eu

for var in KAI_RABBITMQ_ADMIN_PASSWORD KAI_RABBITMQ_API_PASSWORD KAI_RABBITMQ_AI_ENGINE_PASSWORD; do
  eval "value=\${$var:-}"
  case "$value" in
    "") echo "render-definitions: falta a variável $var (gera com scripts/dev/rabbitmq-passwords.sh)" >&2; exit 1 ;;
    changeme*) echo "render-definitions: $var tem o valor de exemplo; gera uma password" >&2; exit 1 ;;
    *[!A-Za-z0-9._-]*) echo "render-definitions: $var só aceita [A-Za-z0-9._-]" >&2; exit 1 ;;
  esac
  if [ "${#value}" -lt 24 ]; then
    echo "render-definitions: $var tem menos de 24 caracteres" >&2
    exit 1
  fi
done

umask 077
mkdir -p /tmp/kai-rabbitmq
awk '{
  gsub(/<KAI_RABBITMQ_ADMIN_PASSWORD>/, ENVIRON["KAI_RABBITMQ_ADMIN_PASSWORD"])
  gsub(/<KAI_RABBITMQ_API_PASSWORD>/, ENVIRON["KAI_RABBITMQ_API_PASSWORD"])
  gsub(/<KAI_RABBITMQ_AI_ENGINE_PASSWORD>/, ENVIRON["KAI_RABBITMQ_AI_ENGINE_PASSWORD"])
  print
}' /etc/rabbitmq/definitions.template.json > /tmp/kai-rabbitmq/definitions.json
chown -R rabbitmq:rabbitmq /tmp/kai-rabbitmq 2>/dev/null || true

unset KAI_RABBITMQ_ADMIN_PASSWORD KAI_RABBITMQ_API_PASSWORD KAI_RABBITMQ_AI_ENGINE_PASSWORD value
exec docker-entrypoint.sh rabbitmq-server
