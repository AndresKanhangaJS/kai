"""Spike M03 E1.1: publica deltas no Reverb a partir de Python, sem Laravel.

Usa só a biblioteca padrão e a API HTTP do protocolo Pusher
(POST /apps/{app_id}/events), assinada com HMAC-SHA256. É o mesmo caminho que
o AI Engine vai usar para os deltas de streaming (ADR-0009).

Variáveis: REVERB_APP_ID, REVERB_APP_KEY, REVERB_APP_SECRET, REVERB_URL,
SPIKE_CHANNEL, SPIKE_COUNT, SPIKE_INTERVAL_MS. O segredo nunca é impresso.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APP_ID = os.environ["REVERB_APP_ID"]
KEY = os.environ["REVERB_APP_KEY"]
SECRET = os.environ["REVERB_APP_SECRET"].encode()
BASE = os.environ.get("REVERB_URL", "http://reverb:8080")
CHANNEL = os.environ["SPIKE_CHANNEL"]
COUNT = int(os.environ.get("SPIKE_COUNT", "100"))
INTERVAL = int(os.environ.get("SPIKE_INTERVAL_MS", "50")) / 1000


def signed_post(path: str, body: dict, secret: bytes) -> int:
    raw = json.dumps(body, separators=(",", ":")).encode()
    params = {
        "auth_key": KEY,
        "auth_timestamp": str(int(time.time())),
        "auth_version": "1.0",
        "body_md5": hashlib.md5(raw).hexdigest(),  # noqa: S324 — exigido pelo protocolo Pusher
    }
    query = "&".join(f"{k}={params[k]}" for k in sorted(params))
    to_sign = f"POST\n{path}\n{query}".encode()
    params["auth_signature"] = hmac.new(secret, to_sign, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        f"{BASE}{path}?{urllib.parse.urlencode(params)}", data=raw, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    path = f"/apps/{APP_ID}/events"

    # Negativo: uma publicação com a assinatura errada tem de ser recusada.
    bad = signed_post(path, {"name": "delta", "channel": CHANNEL, "data": "{}"}, b"segredo-errado")
    print(f"publicacao-mal-assinada status={bad}", flush=True)
    if bad < 400:
        print("FALHA: o Reverb aceitou uma publicação mal assinada", flush=True)
        return 1

    failures = 0
    started = time.perf_counter()
    for seq in range(COUNT):
        data = json.dumps({"seq": seq, "text": f"token-{seq} ", "sent_at_ms": time.time() * 1000})
        status = signed_post(path, {"name": "delta", "channel": CHANNEL, "data": data}, SECRET)
        if status != 200:
            failures += 1
            print(f"delta {seq}: status={status}", flush=True)
        time.sleep(INTERVAL)
    elapsed = time.perf_counter() - started
    print(f"publicados={COUNT - failures}/{COUNT} em {elapsed:.2f}s", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
