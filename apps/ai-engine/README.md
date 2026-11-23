# AI Engine (`apps/ai-engine`)

Serviço Python 3.14 + FastAPI do KAI. Recebe turnos de conversa pelo RabbitMQ, chama o modelo através do `LLMGateway`, envia os deltas pelo Reverb e reporta o resultado em eventos. Não decide nem persiste estado de negócio: isso é do Laravel (ADR-0002).

- **Spec:** [SPEC-004](../../docs/specs/004-ai-engine-m03.md).
- **Contratos:** [`packages/contracts`](../../packages/contracts/README.md).
- **ADRs:** 0006 (LLM), 0010 (rede privada), 0015 (Reverb), 0016 (`aio-pika`), 0017 (OpenTelemetry), 0018 (retry e DLQ).
- **Regras:** [`.claude/rules/python-ai-engine.md`](../../.claude/rules/python-ai-engine.md).

## Estado (M03 E3.2)

Para já só há os endpoints de health, conforme o `health.v1`:
- `GET /health/live`;
- `GET /health/ready`, que dá 200 só com a ligação ao RabbitMQ activa e 503 caso contrário.

O LLM Gateway, o consumidor e o cancelamento entram nas E3.3 a E3.5.

## Correr

O serviço está no profile `messaging` do Compose, porque precisa do RabbitMQ e da password `KAI_RABBITMQ_AI_ENGINE_PASSWORD` (gerada com `scripts/dev/passwords.sh`, ver [`rabbitmq.md`](../../docs/engineering/rabbitmq.md)):

```bash
docker compose --profile messaging up -d --wait ai-engine
```

Não tem porta publicada no host (ADR-0010): só se chega a ele em `http://ai-engine:8000`, a partir das redes `messaging` e `telemetry`.

Não está na rede `default`, por isso não chega ao MySQL nem ao Redis do Laravel (ADR-0002, testado).

O contentor:
- corre como utilizador não-root;
- tem o sistema de ficheiros só de leitura e um `/tmp` `noexec`;
- não tem capabilities nem pip;
- está limitado a 512 MB de memória e 128 processos.

As dependências instalam-se só a partir de wheels (`--only-binary`).

## Qualidade e testes

```bash
scripts/ci/ai-engine.sh     # ruff, ruff format --check, mypy (strict), pytest; sem rede
scripts/ci/integration.sh   # serviço real contra o RabbitMQ da stack kai-it
```

## Dependências (P-021)

- **Declaração:** as versões exactas estão em `requirements.in` (runtime) e `requirements-dev.in` (CI).
- **Locks:** `requirements.txt` e `requirements-dev.txt` têm todas as transitivas com hashes, e a imagem instala-as com `pip install --require-hashes --no-deps`.
- **Regenerar os locks:** `scripts/dev/ai-engine-lock.sh <AAAA-MM-DD>`, em que a data limite de publicação é 14 dias antes do dia em que o corres. O `uv` 0.13.7 serve só para gerar os locks, num contentor descartável.
- **Dependência nova:** pede a aprovação do owner e a verificação da licença.

**Licenças (verificadas no PyPI a 2026-11-23):** MIT, BSD-2/3, Apache-2.0, PSF-2.0 e MPL-2.0 (`certifi`, `pathspec`, usadas sem modificações). Todas são compatíveis com a Apache-2.0 do KAI.

**[P] Aviso conhecido:** o Starlette 1.10 avisa que o `TestClient` sobre o `httpx` está obsoleto e recomenda o `httpx2`. Reavaliar quando subirmos o FastAPI ou o Starlette.
