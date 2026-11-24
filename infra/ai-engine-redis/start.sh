#!/bin/sh
# Redis da inbox do AI Engine (M03 E3.4a; P-020, decisão do owner a 2026-11-23).
# Só o ai-engine lhe chega (rede interna `ai-engine-data`). Endurecimento:
# - o utilizador `default` fica desligado: nenhuma ligação sem autenticação;
# - o único utilizador, `kai-ai-engine`, só lê e escreve `inbox:ai-engine:*` e
#   só tem os comandos da inbox (GET, SET, PING);
# - a password nunca vai na linha de comandos nem fica em claro: o ficheiro
#   ACL (0400, em tmpfs) guarda só o SHA-256, e a variável sai do ambiente
#   antes de o redis-server arrancar.
set -eu

pw="${KAI_AI_ENGINE_REDIS_PASSWORD:-}"
case "$pw" in
  "") echo "ai-engine-redis: falta KAI_AI_ENGINE_REDIS_PASSWORD (gera com scripts/dev/passwords.sh)" >&2; exit 1 ;;
  changeme*) echo "ai-engine-redis: KAI_AI_ENGINE_REDIS_PASSWORD tem o valor de exemplo" >&2; exit 1 ;;
  *[!A-Za-z0-9._-]*) echo "ai-engine-redis: KAI_AI_ENGINE_REDIS_PASSWORD só aceita [A-Za-z0-9._-]" >&2; exit 1 ;;
esac
if [ "${#pw}" -lt 24 ]; then
  echo "ai-engine-redis: KAI_AI_ENGINE_REDIS_PASSWORD tem menos de 24 caracteres" >&2
  exit 1
fi

umask 077
mkdir -p /tmp/kai-redis
hash=$(printf '%s' "$pw" | sha256sum | cut -d' ' -f1)
unset KAI_AI_ENGINE_REDIS_PASSWORD pw
{
  echo "user default off resetkeys resetchannels -@all"
  echo "user kai-ai-engine on #$hash resetkeys ~inbox:ai-engine:* resetchannels -@all +get +set +ping"
} > /tmp/kai-redis/users.acl
chmod 0400 /tmp/kai-redis/users.acl
unset hash

# protected-mode desligado: só protege quem não tem autenticação, e aqui o
# `default` está desligado e a rede é interna. noeviction: a inbox nunca perde
# chaves em silêncio (cheia, o SET falha e a mensagem vai para a DLQ).
exec redis-server \
  --aclfile /tmp/kai-redis/users.acl \
  --protected-mode no \
  --port 6379 \
  --dir /data \
  --appendonly yes \
  --save "" \
  --maxmemory 64mb \
  --maxmemory-policy noeviction
