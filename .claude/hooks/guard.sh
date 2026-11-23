#!/usr/bin/env bash
# PreToolUse (KAI): bloqueia acesso a segredos e comandos perigosos.
# A lógica vive em guard.py (stdlib). Fail-closed: sem python3, bloqueia.
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "KAI guard: BLOQUEADO: python3 não encontrado (corre o Claude Code dentro do WSL)." >&2
  exit 2
fi

exec python3 -I "$(dirname "${BASH_SOURCE[0]}")/guard.py"
