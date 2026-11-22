#!/usr/bin/env bash
# CI do harness e scan de segredos (M02 E2.4, NFR-007): valida a estrutura do
# harness do Claude Code e procura padrões de segredos no repositório; testa o
# hook guard. Complementa o secret scanning nativo do GitHub
# (docs/engineering/ci.md). Uso: scripts/ci/harness.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "→ validate_harness.py (inclui o scan de segredos)"
python3 .claude/scripts/validate_harness.py

echo "→ Testes do hook guard"
bash .claude/hooks/tests/test_guard.sh
