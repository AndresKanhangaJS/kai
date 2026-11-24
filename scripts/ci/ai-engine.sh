#!/usr/bin/env bash
# CI do apps/ai-engine (M03 E3.2, SPEC-004): ruff, ruff format, mypy (strict) e
# pytest. Corre num contentor SEM REDE e sem chaves de fornecedores (AC-004-03).
# Igual na CI e no local. Uso: scripts/ci/ai-engine.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

docker build -q --target dev --build-context contracts=packages/contracts -t kai-ai-engine-ci apps/ai-engine >/dev/null
docker run --rm --network none --read-only --tmpfs /tmp \
  -v "$PWD/packages/contracts:/contracts:ro" -e KAI_CONTRACTS_DIR=/contracts \
  kai-ai-engine-ci
