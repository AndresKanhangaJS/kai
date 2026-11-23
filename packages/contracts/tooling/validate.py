"""Valida packages/contracts (SPEC-003, M02 E2.3).

AC-C1  Cada JSON Schema é válido em draft 2020-12; o OpenAPI e o AsyncAPI
       validam contra os meta-schemas oficiais (com sha256 verificado) e
       todas as referências ($ref) resolvem.
AC-C2  Os exemplos válidos passam.
AC-C3  Os exemplos inválidos falham, e falham pelo erro declarado em
       invalid/expected-errors.json (palavra-chave e caminho).
AC-C4  Os pedidos de autorização com nível, modo ou grant são rejeitados
       (exemplos inválidos dedicados).
AC-C5  As mensagens do RabbitMQ têm user_id obrigatório, não declaram campos
       de grants, tokens ou credenciais (seguindo os $ref) e não têm objectos
       abertos fora da allowlist.

Antes de validar o repositório, o validador testa-se a si próprio com schemas
maus que tem de detectar. Sai com 1 se alguma verificação falhar. Não usa rede.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7, DRAFT202012

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"
META = ROOT / "tooling" / "meta"
BASE = "https://contracts.kai.internal/schemas/"
SHARED = {"common.v1", "envelope.v1"}  # não são mensagens nem corpos
META_SHA256 = {
    "openapi-3.1-2022-10-07.json": "da01ba28852cac0de53893797cb8d1942bc3b05084f526dcc216717dec314ed0",
    "asyncapi-3.0.0.json": "1786a007ac00344a8f529e5a6fc5db786b0be6757e0b94a8b95a8a6a52b7fe9a",
}

# Nomes de campo que sugerem credenciais. As contagens do LLM (*_tokens) são
# permitidas só por nome exacto.
FORBIDDEN_FIELD = re.compile(
    r"(?i)grant|jws|jwt|bearer|auth(?!or)|signature|cookie|session|secret|passw|pwd|"
    r"credential|private_?key|signing_?key|api_?key|otp|token"
)
COUNT_FIELDS = {"input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "max_output_tokens"}
# Objectos sem additionalProperties fechado só são aceites aqui.
OPEN_OBJECT_ALLOWLIST = {f"{BASE}envelope.v1.json#/properties/payload"}

errors: list[str] = []
oks: list[str] = []

checker = FormatChecker()


@checker.checks("date-time", raises=ValueError)
def _date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return True


def ok_if_clean(before: int, message: str) -> None:
    """Regista o OK só se a verificação não acrescentou erros."""
    if len(errors) == before:
        oks.append(message)


# --- carregamento -------------------------------------------------------------

def build_registry(schemas: dict[str, dict]) -> Registry:
    registry: Registry = Registry()
    for doc in schemas.values():
        registry = registry.with_resource(doc["$id"], Resource(contents=doc, specification=DRAFT202012))
    return registry


def load_schemas() -> dict[str, dict]:
    before = len(errors)
    schemas: dict[str, dict] = {}
    for f in sorted(SCHEMAS.glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(doc)
        except Exception as e:  # noqa: BLE001
            errors.append(f"AC-C1 schemas/{f.name}: não é um JSON Schema 2020-12 válido: {e}")
            continue
        if doc.get("$id") != f"{BASE}{f.name}":
            errors.append(f"AC-C1 schemas/{f.name}: $id deve ser {BASE}{f.name}")
        schemas[f.stem] = doc
    ok_if_clean(before, f"AC-C1: {len(schemas)} JSON Schemas válidos (draft 2020-12)")
    return schemas


def check_meta_hashes() -> bool:
    before = len(errors)
    for name, expected in META_SHA256.items():
        actual = hashlib.sha256((META / name).read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"AC-C1 tooling/meta/{name}: sha256 {actual} ≠ {expected} (meta-schema alterado)")
    ok_if_clean(before, "AC-C1: meta-schemas oficiais íntegros (sha256)")
    return len(errors) == before


# --- exemplos -----------------------------------------------------------------

def all_errors(errs: Iterator[ValidationError]) -> Iterator[ValidationError]:
    for e in errs:
        yield e
        yield from all_errors(iter(e.context or []))


def pointer(e: ValidationError) -> str:
    return "".join(f"/{p}" for p in e.absolute_path)


def check_examples(schemas: dict[str, dict], registry: Registry) -> None:
    before = len(errors)
    valid_n = invalid_n = 0
    for name, schema in schemas.items():
        if name in SHARED:
            continue
        v = Draft202012Validator(schema, registry=registry, format_checker=checker)
        valid = sorted((EXAMPLES / name / "valid").glob("*.json"))
        inv_dir = EXAMPLES / name / "invalid"
        invalid = sorted(p for p in inv_dir.glob("*.json") if p.name != "expected-errors.json")
        if not valid or not invalid:
            errors.append(f"AC-C2/C3 {name}: precisa de ≥ 1 exemplo válido e ≥ 1 inválido (E3.3)")
        for f in valid:
            errs = sorted(v.iter_errors(json.loads(f.read_text(encoding="utf-8"))), key=str)
            if errs:
                errors.append(f"AC-C2 examples/{name}/valid/{f.name}: devia passar: {errs[0].message[:200]}")
            valid_n += 1
        expected_f = inv_dir / "expected-errors.json"
        expected = json.loads(expected_f.read_text(encoding="utf-8")) if expected_f.is_file() else {}
        for f in invalid:
            invalid_n += 1
            found = [(e.validator, pointer(e)) for e in all_errors(v.iter_errors(json.loads(f.read_text(encoding="utf-8"))))]
            if not found:
                errors.append(f"AC-C3 examples/{name}/invalid/{f.name}: devia FALHAR e passou")
                continue
            exp = expected.get(f.stem)
            if exp is None:
                errors.append(f"AC-C3 examples/{name}/invalid/{f.name}: falta o erro esperado em expected-errors.json")
            elif (exp["keyword"], exp["path"]) not in found:
                errors.append(
                    f"AC-C3 examples/{name}/invalid/{f.name}: falha por outro motivo; esperado "
                    f"{exp['keyword']} em '{exp['path']}', obtido {sorted(set(found))[:3]}"
                )
        for stale in sorted(set(expected) - {p.stem for p in invalid}):
            errors.append(f"AC-C3 examples/{name}/invalid/expected-errors.json: {stale} não existe")
    for d in sorted(p for p in EXAMPLES.iterdir() if p.is_dir()):
        if d.name not in schemas:
            errors.append(f"examples/{d.name}: não há schemas/{d.name}.json")
    ok_if_clean(before, f"AC-C2/AC-C3/AC-C4: {valid_n} exemplos válidos passam, {invalid_n} inválidos falham pelo erro declarado")


# --- regras do KAI sobre as mensagens (AC-C5) ------------------------------

def walk(contents: object, uri: str, registry: Registry, seen: set[str]) -> Iterator[tuple[str, dict]]:
    """Percorre um schema e tudo o que ele referencia ($ref), devolvendo
    (localização, sub-schema) para cada nó objecto."""

    def go(node: object, loc: str, res) -> Iterator[tuple[str, dict]]:
        if isinstance(node, dict):
            if loc in seen:
                return
            seen.add(loc)
            yield loc, node
            ref = node.get("$ref")
            if isinstance(ref, str):
                resolved = res.lookup(ref)
                doc_uri = ref.split("#", 1)[0] or loc.split("#", 1)[0]
                if not doc_uri.startswith("https://"):
                    doc_uri = BASE + doc_uri
                target = doc_uri + "#" + (ref.split("#", 1)[1] if "#" in ref else "")
                yield from go(resolved.contents, target, resolved.resolver)
            for k, v in node.items():
                if k in ("$ref", "const", "enum", "examples", "default", "description", "title"):
                    continue
                if isinstance(v, dict):
                    yield from go(v, f"{loc}/{k}", res)
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        yield from go(item, f"{loc}/{k}/{i}", res)

    yield from go(contents, uri, registry.resolver(base_uri=uri.split("#")[0]))


def message_rule_violations(name: str, schema: dict, registry: Registry) -> list[str]:
    found: list[str] = []
    props = schema.get("properties", {})
    if props.get("type", {}).get("const") != name or schema.get("title") != name:
        found.append(f"{name}: title e type.const têm de ser o nome do ficheiro")
    if "user_id" not in props.get("payload", {}).get("required", []):
        found.append(f"{name}: payload sem user_id obrigatório (NFR-009)")
    for loc, node in walk(schema, f"{BASE}{name}.json#", registry, set()):
        names = list((node.get("properties") or {}).keys()) + list((node.get("patternProperties") or {}).keys())
        for key in names:
            if FORBIDDEN_FIELD.search(key) and key not in COUNT_FIELDS:
                found.append(f"{name}: campo proibido numa mensagem do RabbitMQ: '{key}' em {loc}")
        if node.get("type") == "object" and node.get("additionalProperties", True) is True and loc not in OPEN_OBJECT_ALLOWLIST:
            found.append(f"{name}: objecto aberto (sem additionalProperties fechado) em {loc}")
    return found


def check_message_rules(schemas: dict[str, dict], registry: Registry) -> list[str]:
    before = len(errors)
    messages = [n for n in schemas if n.startswith(("ai.", "knowledge."))]
    for name in messages:
        errors.extend(f"AC-C5 {m}" for m in message_rule_violations(name, schemas[name], registry))
    ok_if_clean(before, f"AC-C5: {len(messages)} mensagens com user_id, sem campos de credenciais nem objectos abertos")
    return messages


def selftest(schemas: dict[str, dict]) -> None:
    """O validador tem de apanhar estes schemas maus (revisão de segurança da E3)."""
    before = len(errors)
    name = "ai.mission.step.resume.v1"
    base = json.loads(json.dumps(schemas[name]))

    def add(field: str, sub: dict):
        return lambda s, c: s["properties"]["payload"]["properties"].__setitem__(field, sub)

    cases = {
        "campo jws no payload": add("jws", {"type": "string"}),
        "campo Bearer no payload": add("Bearer", {"type": "string"}),
        "access_tokens no payload": add("access_tokens", {"type": "string"}),
        "auth_token escondido em common via $ref": lambda s, c: c["$defs"]["uuid"].update(
            {"type": "object", "additionalProperties": False, "properties": {"auth_token": {"type": "string"}}}),
        "objecto aberto no payload": add("debug", {"type": "object"}),
        "user_id opcional": lambda s, c: s["properties"]["payload"].__setitem__("required", ["mission_id"]),
    }
    for label, mutate in cases.items():
        s = json.loads(json.dumps(base))
        c = json.loads(json.dumps(schemas["common.v1"]))
        mutate(s, c)
        reg = build_registry({**schemas, name: s, "common.v1": c})
        if not message_rule_violations(name, s, reg):
            errors.append(f"AUTO-TESTE: o validador não detectou: {label}")
    ok_if_clean(before, f"auto-teste do validador: {len(cases)} schemas maus detectados")


# --- OpenAPI e AsyncAPI -----------------------------------------------------

def refs(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        if isinstance(node.get("$ref"), str):
            yield node["$ref"]
        for v in node.values():
            yield from refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from refs(v)


def resolve_pointer(doc: object, ptr: str) -> bool:
    cur = doc
    for part in ptr.lstrip("/").split("/") if ptr.strip("/") else []:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def check_refs(label: str, doc: dict, base: Path) -> set[str]:
    external: set[str] = set()
    for ref in refs(doc):
        target, _, ptr = ref.partition("#")
        if target:
            f = (base / target).resolve()
            if not f.is_file():
                errors.append(f"AC-C1 {label}: $ref para ficheiro inexistente: {ref}")
                continue
            external.add(f.stem)
            if ptr and not resolve_pointer(json.loads(f.read_text(encoding="utf-8")), ptr):
                errors.append(f"AC-C1 {label}: $ref com ponteiro inexistente: {ref}")
        elif not resolve_pointer(doc, ptr):
            errors.append(f"AC-C1 {label}: $ref interno inexistente: {ref}")
    return external


def check_openapi(schemas: dict[str, dict]) -> None:
    before = len(errors)
    f = ROOT / "openapi" / "internal-v1.yaml"
    doc = yaml.safe_load(f.read_text(encoding="utf-8"))
    meta = json.loads((META / "openapi-3.1-2022-10-07.json").read_text(encoding="utf-8"))
    for e in sorted(Draft202012Validator(meta).iter_errors(doc), key=str)[:5]:
        errors.append(f"AC-C1 openapi/internal-v1.yaml: {'/'.join(map(str, e.path))}: {e.message[:200]}")
    used = check_refs("openapi/internal-v1.yaml", doc, f.parent)
    bodies = {n for n in schemas if n not in SHARED and not n.startswith(("ai.", "knowledge."))}
    for missing in sorted(bodies - used):
        errors.append(f"AC-C1 schemas/{missing}.json não é usado pelo OpenAPI")
    ok_if_clean(before, f"AC-C1: OpenAPI 3.1 válido; {len(used)} schemas referenciados")


def check_asyncapi(messages: list[str]) -> None:
    before = len(errors)
    f = ROOT / "asyncapi" / "kai-v1.yaml"
    doc = yaml.safe_load(f.read_text(encoding="utf-8"))
    meta = json.loads((META / "asyncapi-3.0.0.json").read_text(encoding="utf-8"))
    registry = (Resource(contents=meta, specification=DRAFT7) @ Registry()).crawl()
    for e in sorted(Draft7Validator(meta, registry=registry).iter_errors(doc), key=str)[:5]:
        errors.append(f"AC-C1 asyncapi/kai-v1.yaml: {'/'.join(map(str, e.path))}: {e.message[:200]}")
    used = check_refs("asyncapi/kai-v1.yaml", doc, f.parent)
    names = {m.get("name") for m in doc.get("components", {}).get("messages", {}).values()}
    for m in sorted(set(messages) - names):
        errors.append(f"AC-C1 {m}: mensagem sem entrada no AsyncAPI")
    for m in sorted(names - set(messages)):
        errors.append(f"AC-C1 AsyncAPI: {m} não tem schema")
    for m in sorted(set(messages) - used):
        errors.append(f"AC-C1 AsyncAPI: schemas/{m}.json não é referenciado")
    ok_if_clean(before, f"AC-C1: AsyncAPI 3.0 válido; {len(names)} mensagens")


def main() -> int:
    schemas = load_schemas()
    if {"common.v1", "envelope.v1", "ai.mission.step.resume.v1"} <= schemas.keys():
        selftest(schemas)
    registry = build_registry(schemas)
    check_examples(schemas, registry)
    messages = check_message_rules(schemas, registry)
    if check_meta_hashes():
        check_openapi(schemas)
        check_asyncapi(messages)
    for m in oks:
        print(f"OK     {m}")
    for m in errors:
        print(f"ERRO   {m}")
    print(f"\nResumo: {len(oks)} OK, {len(errors)} erros")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
