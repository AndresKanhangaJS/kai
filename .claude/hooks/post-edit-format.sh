#!/usr/bin/env bash
# PostToolUse (Edit|Write) (KAI): formata o ficheiro editado SE o toolchain local existir.
# Hoje (antes do M02) não há toolchain, por isso não faz nada (no-op documentado).
# Só usa binários locais do projecto; sem rede; nunca bloqueia (PostToolUse não bloqueia).
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
command -v python3 >/dev/null 2>&1 || exit 0

file="$(python3 -I -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path",""))' 2>/dev/null)" || exit 0
[[ -n "$file" && -f "$file" ]] || exit 0

# Só ficheiros dentro do projecto.
real_root="$(realpath "$root")"
real_file="$(realpath "$file")"
[[ "$real_file" == "$real_root"/* ]] || exit 0
rel="${real_file#"$real_root"/}"

case "$rel" in
  apps/api/*.php|apps/api/**/*.php)
    bin="$real_root/apps/api/vendor/bin/pint"
    [[ -x "$bin" ]] && "$bin" --quiet "$real_file" ;;
  apps/web/*)
    bin="$real_root/apps/web/node_modules/.bin/prettier"
    [[ -x "$bin" ]] && "$bin" --write --log-level warn "$real_file" ;;
  apps/ai-engine/*.py|apps/ai-engine/**/*.py)
    bin="$real_root/apps/ai-engine/.venv/bin/ruff"
    [[ -x "$bin" ]] && "$bin" format --quiet "$real_file" ;;
esac

exit 0
