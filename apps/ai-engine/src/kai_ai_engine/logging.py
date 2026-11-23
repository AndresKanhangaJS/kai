"""Logs JSON estruturados (observability.md): só IDs, códigos e contagens, nunca conteúdo.

`trace_id` e `span_id` entram com o OpenTelemetry (M03 E7.1).
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import override

SERVICE = "kai-ai-engine"
RESERVED = frozenset({"ts", "service", "level", "event", "error_class"})
# Em DEBUG, o aiormq regista frames AMQP (o StartOk leva a resposta SASL PLAIN) e os
# clientes HTTP registam cabeçalhos e corpos (chave da API, prompts, respostas).
QUIET_LIBRARIES = ("aiormq", "aio_pika", "pamqp", "anthropic", "httpx2", "httpcore2", "httpx", "httpcore")


class JsonFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "service": SERVICE,
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            # Os campos extra nunca sobrepõem os reservados (nível, evento, serviço).
            entry.update({k: v for k, v in fields.items() if k not in RESERVED})
        if record.exc_info and record.exc_info[0] is not None:
            # Só a classe: a mensagem de uma excepção pode conter dados.
            entry["error_class"] = record.exc_info[0].__name__
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # O access log do uvicorn fica desligado; o error log passa pelo formato JSON.
    logging.getLogger("uvicorn.access").disabled = True
    for name in QUIET_LIBRARIES:
        logging.getLogger(name).setLevel(max(level, logging.WARNING))
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
