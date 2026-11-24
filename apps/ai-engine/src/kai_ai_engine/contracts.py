"""Validação das mensagens contra os contratos v1 (`packages/contracts`, SPEC-003).

Os schemas vão dentro da imagem (`/app/contracts/schemas`, copiados no build), por isso a
imagem valida sempre contra os contratos do próprio commit. As `$ref` resolvem-se só a partir
desses ficheiros: nunca há pedidos de rede.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

DEFAULT_DIR = Path("/app/contracts")


def contracts_dir() -> Path:
    """`KAI_CONTRACTS_DIR` (CI e testes) ou o caminho na imagem; fora dela, o monorepo."""
    configured = os.environ.get("KAI_CONTRACTS_DIR")
    if configured:
        return Path(configured)
    if DEFAULT_DIR.exists():
        return DEFAULT_DIR
    return Path(__file__).resolve().parents[4] / "packages" / "contracts"


@dataclass(frozen=True)
class Violation:
    """Onde e que regra falhou, sem o valor (pode ser conteúdo do owner)."""

    path: str
    keyword: str

    def __str__(self) -> str:
        return f"{self.path or '/'}:{self.keyword}"


class ContractRegistry:
    def __init__(self, schemas_dir: Path | None = None) -> None:
        directory = schemas_dir or contracts_dir() / "schemas"
        documents: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.glob("*.v[0-9]*.json")):
            documents[path.name] = json.loads(path.read_text(encoding="utf-8"))
        registry: Registry[Any] = Registry().with_resources(
            (doc["$id"], Resource.from_contents(doc, default_specification=DRAFT202012))
            for doc in documents.values()
        )
        self._validators: dict[str, Any] = {}
        for name, doc in documents.items():
            Draft202012Validator.check_schema(doc)
            self._validators[name.removesuffix(".json")] = Draft202012Validator(doc, registry=registry)

    def knows(self, message_type: str) -> bool:
        return message_type in self._validators

    def violations(self, message_type: str, document: object) -> list[Violation]:
        validator = self._validators[message_type]
        return sorted(
            (
                Violation(path="/".join(str(p) for p in error.absolute_path), keyword=str(error.validator))
                for error in validator.iter_errors(document)
            ),
            key=str,
        )
