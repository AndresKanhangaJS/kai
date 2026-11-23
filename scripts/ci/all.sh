#!/usr/bin/env bash
# Corre localmente tudo o que a CI corre. O E2E exige a stack de dev parada
# (`docker compose stop`), porque usa as mesmas portas. Uso: scripts/ci/all.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

scripts/ci/harness.sh
scripts/ci/contracts.sh
scripts/ci/api.sh
scripts/ci/web.sh
scripts/e2e.sh
echo "✓ CI local verde."
