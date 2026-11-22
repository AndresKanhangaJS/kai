#!/usr/bin/env bash
# CI do apps/web (M02 E2.2): typecheck, oxlint e Vitest.
# Igual na CI (GitHub Actions) e no local. Uso: scripts/ci/web.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

# npm ci: node_modules exactamente como no package-lock.json.
docker compose run --rm --no-deps -T web sh -c '
  set -e
  echo "→ npm ci"
  npm ci --no-audit --no-fund
  echo "→ TypeScript (tsc -b)"
  npx tsc -b
  echo "→ oxlint"
  npm run lint
  echo "→ Vitest"
  npm test
'
