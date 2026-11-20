#!/usr/bin/env bash
# SessionStart (KAI): imprime um resumo curto do estado. O stdout entra no contexto.
# Só lê ficheiros do repositório; sem rede; nunca falha a sessão.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
status="$root/docs/STATUS.md"
analysis="$root/docs/product/analysis.md"

branch="$(git -C "$root" branch --show-current 2>/dev/null || echo '?')"
dirty="$(git -C "$root" status --porcelain --untracked-files=all 2>/dev/null | wc -l | tr -d ' ')"

echo "KAI · resumo de arranque"
echo "Branch: ${branch:-?} · ficheiros alterados/por commitar: ${dirty}"

if [[ -f "$status" ]]; then
  grep -m1 -E '^- \*\*Milestone actual:\*\*' "$status" | sed 's/^- //' || true
  echo "Próximas tarefas:"
  awk '/^## Próximas 3 tarefas/{f=1;next} /^## /{f=0} f && /^[0-9]+\./' "$status" | head -n 3
else
  echo "docs/STATUS.md não encontrado."
fi

if [[ -f "$analysis" ]]; then
  pending="$(grep -c -E '^\| P-[0-9]{3} ' "$analysis" || true)"
  echo "Decisões pendentes (P-xxx): ${pending} · ver docs/product/analysis.md §4.2"
fi

exit 0
