#!/usr/bin/env python3
"""Valida o harness do Claude Code no KAI (só stdlib; sem rede; só leitura).

Uso: python3 -I .claude/scripts/validate_harness.py   → exit 0 se não houver ERROS.

Verifica: CLAUDE.md (tamanho, imports), skills e subagentes (frontmatter, limites),
regras (tamanho, paths), settings.json (JSON, hooks referenciados), links internos
dos .md (ficheiro e âncora), padrões de segredos e pastas que não devem existir.

Limitação: o parser de frontmatter suporta o subconjunto YAML usado aqui
(chave: valor e listas "- item"); não é um parser YAML completo.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors: list[str] = []
warnings: list[str] = []
oks: list[str] = []

AGENT_MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
KNOWN_TOOLS = {
    "Read", "Grep", "Glob", "Edit", "Write", "Bash", "WebFetch", "WebSearch",
    "NotebookEdit", "TodoWrite", "Agent",
}
BOOL_VALUES = {"true", "false", "yes", "no", "on", "off", "1", "0"}
MANUAL_SKILLS = {"status", "done"}
REQUIRED_SKILLS = {
    "kai-spec", "kai-adr", "kai-c4", "kai-contract", "kai-tool-definition",
    "kai-agent-definition", "kai-threat-model", "kai-eval", "kai-review",
    "kai-milestone", "kai-db-migration", "kai-observability", "status", "done",
}
REQUIRED_AGENTS = {
    "kai-architect", "kai-laravel-engineer", "kai-react-engineer",
    "kai-python-ai-engineer", "kai-qa-engineer", "kai-security-reviewer",
    "kai-devops-engineer", "kai-ai-eval-engineer", "kai-docs-writer", "kai-verifier",
}
READ_ONLY_AGENTS = {"kai-architect", "kai-security-reviewer", "kai-verifier"}
WRITE_TOOLS = {"Edit", "Write", "Bash", "NotebookEdit"}
FORBIDDEN_PATHS = [  # M02 introduz apps/, packages/, docker-compose.yml (E1) e .github/workflows (E2); revisto 2026-11-22
    "services", "infrastructure",
    "LICENSE", ".mcp.json",
]
EXCLUDED_DIRS = {"vendor", "node_modules", "dist", "dist-ssr", "build", ".git"}
SECRET_PATTERNS = {  # revisto na E2 (revisão de segurança, 2026-11-22)
    "chave Anthropic/OpenAI": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "chave privada PEM": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "token GitHub": re.compile(r"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}"),
    "token Slack": re.compile(r"\bx(?:ox[baprs]|app)-[A-Za-z0-9-]{10,}"),
    "chave Google API": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "APP_KEY do Laravel": re.compile(r"APP_KEY\s*=\s*base64:[A-Za-z0-9+/]{20,}"),
    # Código e configuração: chave (com ou sem aspas, sufixos como _secret) e
    # valor entre aspas. Cobre PHP (=>), JSON/YAML ("token": "…") e JS/Python.
    "atribuição de segredo": re.compile(
        r"(?i)(?<![A-Za-z])(?:password|passwd|secret|api[_-]?key|token|private[_-]?key)[A-Za-z_]*['\"]?"
        r"\s*(?:=>|:|=)\s*['\"]([^'\"\s]{8,})['\"]"
    ),
    # Ficheiros de ambiente: NOME_COM_SEGREDO=valor sem aspas (ex.: DB_PASSWORD=…).
    "variável de ambiente com segredo": re.compile(
        r"(?m)^[ \t]*(?:export[ \t]+)?[A-Z0-9_]*(?:PASSWORD|SECRET|API_KEY|TOKEN|PRIVATE_KEY)[A-Z0-9_]*"
        r"=([^\s'\"#$(][^\s#()]{7,})"
    ),
}
# Valores que são claramente marcadores, não segredos (evita falsos positivos).
PLACEHOLDER_VALUE = re.compile(r"(?i)example|changeme|placeholder|your[-_]|<[^>]*>|^x{6,}$|\*{3,}|redacted")
MAX_SCAN_BYTES = 2_000_000


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def parse_frontmatter(text: str) -> dict[str, object] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    data: dict[str, object] = {}
    key: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            data[key] = value.strip("'\"") if value else []
        elif key and re.match(r"^\s+-\s+", line):
            item = re.sub(r"^\s+-\s+", "", line).strip().strip("'\"")
            if isinstance(data.get(key), list):
                data[key].append(item)  # type: ignore[union-attr]
    return None  # sem fecho


def line_count(p: Path) -> int:
    return len(p.read_text(encoding="utf-8").splitlines())


def check_claude_md() -> None:
    p = ROOT / "CLAUDE.md"
    if not p.exists():
        errors.append("CLAUDE.md não existe")
        return
    n = line_count(p)
    (oks if n <= 150 else errors).append(f"CLAUDE.md tem {n} linhas (limite 150)")
    text = strip_code(p.read_text(encoding="utf-8"))
    for imp in re.findall(r"(?:^|\s)@([\w./-]+\.md)", text):
        target = (p.parent / imp)
        (oks if target.exists() else errors).append(f"CLAUDE.md importa @{imp}: {'existe' if target.exists() else 'NÃO existe'}")


def check_skills() -> None:
    base = ROOT / ".claude" / "skills"
    found = set()
    for skill_md in sorted(base.glob("*/SKILL.md")):
        name_dir = skill_md.parent.name
        found.add(name_dir)
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        where = rel(skill_md)
        if fm is None:
            errors.append(f"{where}: frontmatter ausente ou não fechado")
            continue
        if fm.get("name") != name_dir:
            errors.append(f"{where}: name '{fm.get('name')}' ≠ pasta '{name_dir}'")
        desc = str(fm.get("description", ""))
        if not desc:
            errors.append(f"{where}: description em falta")
        elif len(desc) > 1536:
            errors.append(f"{where}: description com {len(desc)} caracteres (> 1536)")
        dmi = fm.get("disable-model-invocation")
        if dmi is not None and str(dmi).lower() not in BOOL_VALUES:
            errors.append(f"{where}: disable-model-invocation inválido '{dmi}'")
        if name_dir in MANUAL_SKILLS and str(dmi).lower() != "true":
            errors.append(f"{where}: skill manual sem disable-model-invocation: true")
        n = line_count(skill_md)
        if n >= 150:
            errors.append(f"{where}: {n} linhas (limite < 150)")
        for link in re.findall(r"\]\(([^)#]+)\)", skill_md.read_text(encoding="utf-8")):
            if not link.startswith(("http", "mailto:")) and not (skill_md.parent / link).exists():
                errors.append(f"{where}: ficheiro de apoio em falta '{link}'")
        oks.append(f"skill {name_dir}: frontmatter válido, {n} linhas, description {len(desc)} car.")
    missing = REQUIRED_SKILLS - found
    if missing:
        errors.append(f"skills em falta: {sorted(missing)}")


def check_agents() -> None:
    base = ROOT / ".claude" / "agents"
    found = set()
    for f in sorted(base.glob("*.md")):
        where = rel(f)
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{where}: frontmatter ausente ou não fechado")
            continue
        name = str(fm.get("name", ""))
        found.add(name)
        if name != f.stem:
            errors.append(f"{where}: name '{name}' ≠ ficheiro '{f.stem}'")
        desc = str(fm.get("description", ""))
        if not desc:
            errors.append(f"{where}: description em falta")
        elif "proactivamente" not in desc.lower():
            warnings.append(f"{where}: description sem 'proactivamente'")
        model = str(fm.get("model", ""))
        if model not in AGENT_MODELS and not model.startswith("claude-"):
            errors.append(f"{where}: model inválido '{model}'")
        tools_raw = fm.get("tools")
        tools = tools_raw if isinstance(tools_raw, list) else [t.strip() for t in str(tools_raw or "").split(",") if t.strip()]
        if not tools:
            errors.append(f"{where}: tools omitido (herdaria todas as ferramentas)")
        unknown = [t for t in tools if t not in KNOWN_TOOLS and not t.startswith(("Bash(", "mcp__"))]
        if unknown:
            errors.append(f"{where}: ferramentas desconhecidas {unknown}")
        if name in READ_ONLY_AGENTS and WRITE_TOOLS.intersection(tools):
            errors.append(f"{where}: agente só-leitura com ferramentas de escrita {sorted(WRITE_TOOLS.intersection(tools))}")
        oks.append(f"agente {name}: model={model}, tools={','.join(tools)}")
    missing = REQUIRED_AGENTS - found
    if missing:
        errors.append(f"subagentes em falta: {sorted(missing)}")


def check_rules() -> None:
    for f in sorted((ROOT / ".claude" / "rules").glob("*.md")):
        where = rel(f)
        n = line_count(f)
        if n > 45:
            errors.append(f"{where}: {n} linhas (alvo ~40, máx. 45)")
        text = f.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if text.startswith("---"):
            if fm is None or not fm.get("paths"):
                errors.append(f"{where}: frontmatter sem 'paths' válido")
            else:
                oks.append(f"regra {f.stem}: {n} linhas, paths={fm['paths']}")
        else:
            oks.append(f"regra {f.stem}: {n} linhas, global")


def check_settings() -> None:
    p = ROOT / ".claude" / "settings.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"settings.json inválido: {exc}")
        return
    perms = data.get("permissions", {})
    for k in ("allow", "ask", "deny"):
        if not isinstance(perms.get(k), list) or not perms.get(k):
            errors.append(f"settings.json: permissions.{k} vazio ou ausente")
    oks.append(f"settings.json: JSON válido; allow={len(perms.get('allow', []))} ask={len(perms.get('ask', []))} deny={len(perms.get('deny', []))}")
    for event, groups in (data.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = str(h.get("command", "")).replace("${CLAUDE_PROJECT_DIR}", str(ROOT))
                script = Path(cmd.split()[0]) if cmd else None
                if script and script.suffix in {".sh", ".py"}:
                    ok = script.exists() and os.access(script, os.X_OK)
                    (oks if ok else errors).append(f"hook {event}: {rel(script) if script.exists() else script} {'existe e é executável' if ok else 'em falta ou sem +x'}")
    if not data.get("hooks"):
        warnings.append("settings.json: sem hooks registados (ainda)")
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    (oks if ".claude/settings.local.json" in gi else errors).append(".gitignore inclui .claude/settings.local.json")
    for s in sorted((ROOT / ".claude" / "hooks").glob("*.sh")):
        (oks if os.access(s, os.X_OK) else errors).append(f"{rel(s)} {'executável' if os.access(s, os.X_OK) else 'SEM +x'}")


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def slug(heading: str) -> str:
    h = heading.strip().lower()
    h = "".join(ch for ch in h if unicodedata.category(ch)[0] in "LN" or ch in " -_")
    return h.replace(" ", "-")


def anchors_of(p: Path) -> set[str]:
    text = re.sub(r"```.*?```", "", p.read_text(encoding="utf-8"), flags=re.S)
    return {slug(m) for m in re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.M)}


def md_files() -> list[Path]:
    return [p for p in ROOT.rglob("*.md") if not EXCLUDED_DIRS & set(p.parts)]


def check_links() -> None:
    total = 0
    for f in md_files():
        for link in re.findall(r"\]\(([^)\s]+)\)", strip_code(f.read_text(encoding="utf-8"))):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            total += 1
            path_part, _, anchor = link.partition("#")
            target = f if not path_part else (f.parent / path_part)
            if not target.exists():
                errors.append(f"{rel(f)}: link partido → {link}")
                continue
            if anchor and target.is_file() and target.suffix == ".md" and anchor not in anchors_of(target):
                errors.append(f"{rel(f)}: âncora inexistente → {link}")
    oks.append(f"links internos verificados: {total}")


def scan_targets() -> list[Path]:
    """Ficheiros a analisar: os que o git conhece ou conheceria (versionados e
    novos não ignorados). Nunca lê ficheiros ignorados, como os de ambiente
    locais (security.md)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        warnings.append("scan de segredos: git indisponível; a usar a árvore de ficheiros")
        return [p for p in ROOT.rglob("*") if p.is_file() and not (EXCLUDED_DIRS & set(p.parts))]
    paths = [ROOT / name for name in out.decode("utf-8").split("\0") if name]
    return [p for p in paths if p.is_file() and not (EXCLUDED_DIRS & set(p.relative_to(ROOT).parts))]


def check_secrets() -> None:
    scanned = 0
    for p in scan_targets():
        try:
            if p.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binário ou ilegível
        scanned += 1
        for label, rx in SECRET_PATTERNS.items():
            for m in rx.finditer(text):
                value = m.group(1) if rx.groups else m.group(0)
                if PLACEHOLDER_VALUE.search(value):
                    continue
                errors.append(f"{rel(p)}: possível segredo ({label}) na linha {text[:m.start()].count(chr(10)) + 1}")
    oks.append(f"scan de segredos: {scanned} ficheiros (git ls-files), padrões={len(SECRET_PATTERNS)}")


def check_forbidden() -> None:
    present = [x for x in FORBIDDEN_PATHS if (ROOT / x).exists()]
    if present:
        errors.append(f"ainda não devem existir (pré-M09/M10 ou sem aprovação): {present}")
    else:
        oks.append(f"ainda sem: {', '.join(FORBIDDEN_PATHS)}")


def main() -> int:
    for check in (check_claude_md, check_skills, check_agents, check_rules,
                  check_settings, check_links, check_secrets, check_forbidden):
        check()
    for m in oks:
        print(f"OK     {m}")
    for m in warnings:
        print(f"AVISO  {m}")
    for m in errors:
        print(f"ERRO   {m}")
    print(f"\nResumo: {len(oks)} OK, {len(warnings)} avisos, {len(errors)} erros")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
