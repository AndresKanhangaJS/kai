#!/usr/bin/env bash
# CI de contratos (M02 E2.3, SPEC-003): schemas, OpenAPI, AsyncAPI e exemplos.
# Corre numa imagem própria, sem rede no passo de validação.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "→ construir o validador de contratos"
docker build -q -t kai-contracts-validator packages/contracts/tooling >/dev/null

echo "→ validar packages/contracts"
docker run --rm --network none --read-only \
  --cap-drop=ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m \
  -v "$PWD/packages/contracts:/contracts:ro" \
  kai-contracts-validator
