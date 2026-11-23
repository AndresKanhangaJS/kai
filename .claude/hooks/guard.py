#!/usr/bin/env python3
"""KAI PreToolUse guard.

Bloqueia (exit 2 + motivo em stderr, mecanismo documentado em
code.claude.com/docs/en/hooks):
  - leitura/escrita de ficheiros de segredos (.env*, chaves, credenciais);
  - sudo/doas/su/pkexec;
  - git push com --force / -f / +refspec;
  - rm recursivo (com ou sem -f) fora de caminhos seguros;
  - curl/wget canalizados ou substituídos para uma shell/intérprete.

Exit 0 sem output = segue o fluxo normal de permissões (não aprova nada).
Só usa a stdlib; corre com `python3 -I`. Não faz rede nem escreve ficheiros.

Também bloqueia `git commit/push --no-verify` e apagar branches remotas
(proibidos em .claude/rules/git-workflow.md).

O comando Bash é analisado duas vezes: tal como vem e numa forma normalizada
(sem aspas nem barras invertidas, com `$(`, crases e `-c`/`eval` tratados como
separadores), para apanhar `bash -c "…"`, `eval "…"`, `.e""nv`, `.e\\nv`.
Nomes com glob (`.env*`, `.en[v]`) são comparados com nomes de segredos.

Limitação conhecida: inspecciona o texto do comando; não é uma sandbox.
Ex.: `grep -r TOKEN .`, variáveis (`f=.e; cat ${f}nv`) ou scripts escritos e
depois executados escapam. Ver docs/engineering/claude-code-setup.md §4.
"""
from __future__ import annotations

import fnmatch
import json
import re
import shlex
import sys
from pathlib import PurePosixPath, PureWindowsPath

# --- Segredos -----------------------------------------------------------------
ALLOWED_SECRET_LOOKALIKES = {".env.example", ".env.sample", ".env.dist"}
SECRET_NAME = re.compile(
    r"""^(
        \.env(\..+)?                              # .env, .env.local, .env.production
      | .+\.(pem|key|p12|pfx|jks|keystore|asc)    # chaves e keystores
      | id_(rsa|dsa|ecdsa|ed25519)                # chaves SSH privadas (.pub é permitido)
      | (.+[._-])?credentials(\.[a-z]+)?          # credentials, aws-credentials.json, ...
      | \.netrc | \.npmrc | \.pypirc | \.git-credentials
      | secrets?\.(json|ya?ml|toml|env)
    )$""",
    re.IGNORECASE | re.VERBOSE,
)
SECRET_DIRS = {".ssh", ".aws", ".gnupg", ".kube", "gcloud", ".azure"}

# --- rm -rf: alvos seguros (relativos, dentro do workspace) ---------------------
SAFE_RM_COMPONENTS = {
    "node_modules", "vendor", "dist", "build", "coverage", "tmp", ".tmp", ".cache",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__", ".venv",
}

# Nomes representativos de segredos, para comparar com globs (`.env*`, `*.pem`).
SECRET_SAMPLES = [
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "server.pem",
    "server.key", "credentials", "aws-credentials.json", ".netrc", "secrets.json",
]
GLOB_CHARS = set("*?[")

SHELLS = r"(?:ba|z|da|k|fi)?sh|python[0-9.]*|perl|ruby|node|php"
_PATH = r"(?:\S*/)?"
PIPE_TO_SHELL = re.compile(
    rf"\b(?:curl|wget)\b.*?\|\s*{_PATH}(?:sudo\s+(?:-\S+\s+)*)?{_PATH}"
    rf"(?:env\s+(?:-\S+\s+|\S+=\S+\s+)*)?{_PATH}(?:{SHELLS})\b",
    re.DOTALL,
)
SUBST_TO_SHELL = re.compile(
    rf"(?:^|[\s;&|(/]){_PATH}(?:{SHELLS})\b.*?(?:<\(|\$\(|`)\s*(?:curl|wget)\b",
    re.DOTALL,
)
SUDO = re.compile(r"(?:^|[;&|(\s/`'\"])(?:sudo|doas|pkexec|su)(?:\s|$|[`'\"])")
SEGMENT_SPLIT = re.compile(r"\|\||&&|[;|&\n]")
WORDS = re.compile(r"""[^\s;&|<>()`'"=,]+""")
# Normalização: o que está dentro de `bash -c "…"`, `eval "…"`, `$(…)` e crases
# passa a ser analisado como comando de topo.
NESTED_MARKERS = re.compile(r"\$\(|`|\b(?:eval|exec)\b|\s-c\s")


def deny(reason: str) -> None:
    print(
        f"KAI guard: BLOQUEADO: {reason}. "
        "Se for legítimo, pede ao owner para o fazer manualmente.",
        file=sys.stderr,
    )
    sys.exit(2)


def path_parts(raw: str) -> list[str]:
    """Componentes de um caminho POSIX ou Windows."""
    if "\\" in raw:
        return list(PureWindowsPath(raw).parts)
    return list(PurePosixPath(raw).parts)


def secret_reason(raw: str) -> str | None:
    if not raw:
        return None
    parts = path_parts(raw.strip())
    if not parts:
        return None
    hits = SECRET_DIRS.intersection(parts)
    if hits:
        return f"acesso a directório de credenciais '{sorted(hits)[0]}'"
    name = parts[-1]
    if name in ALLOWED_SECRET_LOOKALIKES:
        return None
    if SECRET_NAME.match(name):
        return f"acesso a ficheiro de segredos '{name}'"
    if GLOB_CHARS.intersection(name) and glob_may_match_secret(name):
        return f"glob que pode apanhar ficheiros de segredos '{name}'"
    return None


def glob_may_match_secret(pattern: str) -> bool:
    """Um glob com parte literal pode expandir para um nome de segredo?

    Globs só com curingas (`*`, `*.*`) são ignorados, para não bloquear `ls *`.
    Como na shell, `*` não apanha ficheiros começados por ponto.
    """
    if not pattern.strip("*?.[]"):
        return False
    for sample in SECRET_SAMPLES:
        if sample.startswith(".") and not pattern.startswith((".", "[")):
            continue
        if fnmatch.fnmatchcase(sample.lower(), pattern.lower()):
            return True
    return False


def split_tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def check_git(tokens: list[str]) -> None:
    if "git" not in tokens:
        return
    rest = tokens[tokens.index("git") + 1:]
    if ("commit" in rest or "push" in rest) and "--no-verify" in rest:
        deny("git com '--no-verify'")
    if "push" not in rest:
        return
    for tok in rest[rest.index("push") + 1:]:
        if tok.startswith("--force") or tok == "--mirror":
            deny(f"git push com '{tok}'")
        if re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", tok):
            deny(f"git push com '{tok}' (force)")
        if tok.startswith("+") and len(tok) > 1:
            deny(f"git push com refspec forçado '{tok}'")
        if tok in {"--delete", "-d"} or (tok.startswith(":") and len(tok) > 1):
            deny(f"git push que apaga uma branch remota ('{tok}')")


def rm_target_is_safe(target: str) -> bool:
    if not target or target.startswith(("/", "~", "$", "-")) or "*" in target:
        return False
    parts = PurePosixPath(target).parts
    if ".." in parts or target in {".", "./"}:
        return False
    return bool(SAFE_RM_COMPONENTS.intersection(parts))


def check_rm(tokens: list[str]) -> None:
    for i, tok in enumerate(tokens):
        if tok != "rm" and not tok.endswith("/rm"):
            continue
        args = tokens[i + 1:]
        short = "".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--"))
        # Recursivo basta (com ou sem -f): `rm -r` também apaga sem perguntar.
        if not ("r" in short or "R" in short or "--recursive" in args):
            continue
        targets = [a for a in args if not a.startswith("-")]
        if not targets:
            deny("rm recursivo sem alvo explícito (ex.: via xargs)")
        unsafe = [t for t in targets if not rm_target_is_safe(t)]
        if unsafe:
            deny(f"rm recursivo fora de caminhos seguros: {' '.join(unsafe)}")


def normalize(command: str) -> str:
    """Remove aspas e escapes; expõe comandos aninhados como segmentos de topo."""
    flat = command.replace("\\\n", " ")
    flat = re.sub(r"[\"'\\]", "", flat)
    return NESTED_MARKERS.sub(" ; ", flat).replace(")", " ; ")


def check_bash_text(command: str) -> None:
    if SUDO.search(command):
        deny("uso de sudo/doas/su/pkexec")
    if PIPE_TO_SHELL.search(command) or SUBST_TO_SHELL.search(command):
        deny("download canalizado para shell/intérprete (curl|wget … | sh)")
    for word in WORDS.findall(command):
        reason = secret_reason(word)
        if reason:
            deny(f"comando com {reason}")
    for segment in SEGMENT_SPLIT.split(command):
        tokens = split_tokens(segment)
        check_git(tokens)
        check_rm(tokens)


def check_bash(command: str) -> None:
    check_bash_text(command)
    check_bash_text(normalize(command))


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        deny("input do hook ilegível (fail-closed)")
    if not isinstance(data, dict):
        deny("input do hook com formato inesperado (fail-closed)")
    tool = data.get("tool_name", "")
    tin = data.get("tool_input") or {}
    if not isinstance(tool, str) or not isinstance(tin, dict):
        deny("input do hook com formato inesperado (fail-closed)")

    if tool == "Bash":
        check_bash(str(tin.get("command", "")))
    elif tool in {"Read", "Edit", "Write", "MultiEdit"}:
        reason = secret_reason(str(tin.get("file_path", "")))
        if reason:
            deny(reason)
    elif tool == "NotebookEdit":
        reason = secret_reason(str(tin.get("notebook_path", "")))
        if reason:
            deny(reason)
    elif tool == "Grep":
        for key in ("path", "glob"):
            reason = secret_reason(str(tin.get(key, "")))
            if reason:
                deny(f"Grep sobre {reason}")
    sys.exit(0)


if __name__ == "__main__":
    main()
