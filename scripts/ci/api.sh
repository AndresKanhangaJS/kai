#!/usr/bin/env bash
# CI do apps/api (M02 E2.1): Pint, PHPStan (Larastan, nível 6) e Pest.
# Igual na CI (GitHub Actions) e no local. Uso: scripts/ci/api.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

# --no-deps: nenhum destes passos precisa de MySQL nem de Redis.
# As variáveis forçadas aqui (e não só no phpunit.xml) garantem que os testes
# correm no SQLite em memória, nunca no MySQL do Compose (bug da E4.4).
run() { docker compose run --rm --no-deps -T "$@"; }

echo "→ Pint (formatação)"
run api vendor/bin/pint --test

echo "→ PHPStan (Larastan, nível 6)"
run api vendor/bin/phpstan analyse --no-progress --memory-limit=1G

echo "→ Pest"
run -e APP_ENV=testing -e DB_CONNECTION=sqlite -e DB_DATABASE=:memory: api vendor/bin/pest
