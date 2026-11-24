# AI Engine (`apps/ai-engine`)

Serviço Python 3.14 + FastAPI do KAI. Recebe turnos de conversa pelo RabbitMQ, chama o modelo através do `LLMGateway`, envia os deltas pelo Reverb e reporta o resultado em eventos. Não decide nem persiste estado de negócio: isso é do Laravel (ADR-0002).

- **Spec:** [SPEC-004](../../docs/specs/004-ai-engine-m03.md).
- **Contratos:** [`packages/contracts`](../../packages/contracts/README.md).
- **ADRs:** 0006 (LLM), 0010 (rede privada), 0015 (Reverb), 0016 (`aio-pika`), 0017 (OpenTelemetry), 0018 (retry e DLQ).
- **Regras:** [`.claude/rules/python-ai-engine.md`](../../.claude/rules/python-ai-engine.md).

## Estado (M03 E3.4a)

Endpoints de health, conforme o `health.v1`:
- `GET /health/live`;
- `GET /health/ready`, que dá 200 só com o RabbitMQ ligado, o consumidor activo e o Redis da inbox a responder (`checks`: `rabbitmq`, `consumer`, `redis`); senão, 503.

## Consumidor de turnos (E3.4a, SPEC-004 §3)

Consome `ai-engine.commands` (`consumer.py`, `prefetch` 4) e trata cada `ai.conversation.turn.requested.v1` em `turns.py`:

1. **Validação, antes de gastar** (AC-004-04): `user_id` AMQP igual a `kai-api`, JSON válido, schema do tipo (`contracts.py`, com os schemas copiados para a imagem no build), routing key igual ao tipo e `tools` vazio (ferramentas só no M05). Uma falha vai para a DLQ (`reject` sem requeue), com o log `message_rejected` (motivo e caminhos das violações, nunca valores).
2. **Inbox** (AC-004-05, `inbox.py`): `SET NX` em `inbox:ai-engine:{id}`. Se já estiver `done`, confirma sem efeito. Se estiver `processing` (processamento interrompido), retoma e regista `inbox_takeover`. Uma reentrega do mesmo `id` enquanto o original corre no mesmo processo espera por ele.
3. **Orçamento** (AC-004-07): `count_tokens` e `estimate_max_cost` antes de qualquer geração; se exceder o `max_cost_usd`, sai `turn.failed(budget_exceeded)` sem chamada nem usage.
4. **Geração** com o prazo do turno contado desde a recepção. Retry com backoff e jitter só antes do primeiro delta, enquanto houver tempo (AC-004-09, até 5 tentativas) e enquanto o pior caso couber no orçamento: uma tentativa que o fornecedor já facturou (input ou raciocínio, mesmo sem texto) conta com o seu custo máximo (revisão de segurança da E3.4a). Num timeout, num erro interno ou no shutdown regista o consumo parcial (AC-004-06).
5. **Eventos** (`events.py`): um `usage.recorded` por chamada com consumo (o modelo e o fornecedor vêm do gateway, nunca da mensagem) e um `turn.completed` ou `turn.failed`. Cada evento é validado contra o schema antes de sair. `causation_id` = `id` do comando, mesmo `correlation_id`, mesmo trace com um span novo.
6. **Publicação com confirms** (`publisher.py`), com `user_id=kai-ai-engine` e `mandatory`. Só depois: `mark_done` e `ack`. Sem confirm (3 tentativas), DLQ e nunca `ack` (o requeue voltaria a pagar a geração a cada entrega). Com o Redis da inbox em baixo, nada foi gasto: volta à fila (`nack` com requeue) e o `x-delivery-limit` acaba na DLQ. Se só o `mark_done` falhar, confirma na mesma (os eventos já saíram).

- **Respostas que não se entregam:** recusa do modelo, paragem inesperada, texto vazio ou com mais de 100 000 caracteres dão `turn.failed(provider_error)`, com o usage.
- **Outros comandos:** um `cancel.requested` válido é confirmado sem efeito até à E3.5; o `step.resume` (M05) vai para a DLQ.
- **Prompt de sistema:** `src/kai_ai_engine/prompts/conversation/v1.md` (versão `conversation/v1`, só nos logs; P-022). As mensagens do owner entram como `user`.
- **Shutdown:** pára a reconexão, deixa de consumir, espera até 10 s pelos turnos a meio, publica o usage parcial dos interrompidos (até 3 s) e devolve-os à fila (`nack` com requeue). O Compose dá 20 s (`stop_grace_period`) antes do SIGKILL.
- **Canais:** se o canal de consumo ou o de publicação fechar sem a ligação cair, a ligação é fechada e recriada; a readiness exige os dois abertos.
- **Arranque:** falha se faltar algum dos 6 schemas de que precisa. Os IDs com `\n` final (aceite pelo `$` das patterns) vão para a DLQ.
- **[H] Uma só réplica:** a inbox retoma logo um `processing`, sem saber se o dono ainda está vivo. Com mais réplicas, precisa de um token de dono (SPEC-004 §6).
- **Reconexão própria (`amqp.py`):** **[C]** com o `connect_robust` do `aio-pika` 10.2.3, ao reiniciar o broker, os canais voltavam mas o consumidor não (`consumer_count 0`) e a readiness continuava a 200 (testado na E3.4a). Agora, quando a ligação cai, liga-se outra vez com backoff e o consumidor recria os canais e o `basic.consume`. A decisão do ADR-0016 (`aio-pika`) mantém-se.
- **Logs:** `turn_started`, `turn_finished{outcome, reason, attempts, usage_events, latency_ms}`, `message_rejected`, `inbox_duplicate`, `inbox_takeover`, `llm_retry`, `infra_retry`. Só IDs, códigos e contagens (teste-canário).

**Redis da inbox** (`ai-engine-redis`, decisão do owner a 2026-11-23, P-020): serviço próprio, com a mesma imagem `redis:8` por digest, na rede interna `ai-engine-data` (só o ai-engine). Sem portas, `read_only`, sem capabilities, AOF num volume próprio e `noeviction`. O `infra/ai-engine-redis/start.sh` desliga o utilizador `default` e cria o `kai-ai-engine` só com `GET`, `SET` e `PING` em `inbox:ai-engine:*`. A password (`KAI_AI_ENGINE_REDIS_PASSWORD`, ≥ 24 caracteres) fica só como SHA-256 no ficheiro ACL e sai do ambiente antes de o servidor arrancar (testado no `integration.sh`).

**[P] Fica para a E3.4b:** os deltas no Reverb com `seq`, o `delta_count` e a AC-004-10. **[H]** Um turno com fallback do lado do servidor dá um só `usage.recorded` (SPEC-004 §3.1), com o modelo final e o custo da cadeia inteira; o detalhe por tentativa fica no log.

## LLM Gateway (`src/kai_ai_engine/llm/`, ADR-0006)

- **Porta (`gateway.py`):** tipos canónicos (`GenerationRequest`, `TextDelta`, `Completed` com `Usage` por tentativa), `stream`, `count_tokens`, `generate` e flags de capacidade (`streaming`, `exact_token_count`, `priced`, `tools=False`). Sem ferramentas no M03.
- **Fornecedor:** vem só da configuração (`MODEL_PROVIDER`, por omissão `fake`), nunca da mensagem. Um fornecedor real sem chave, ou um modelo sem preço, falha no arranque.
- **`fake`:** determinístico, sem rede; `KAI_FAKE_DELAY_PER_DELTA`, `KAI_FAKE_WORDS_PER_DELTA`, `KAI_FAKE_FAIL_BEFORE_FIRST_DELTA`, `KAI_FAKE_FAIL_AFTER_DELTAS` e `KAI_FAKE_SCRIPT` servem os testes de integração.
- **Anthropic:** SDK oficial, assíncrono; `ANTHROPIC_MODEL` (por omissão `claude-opus-5-5`), `ANTHROPIC_EFFORT` (por omissão `medium`), `ANTHROPIC_FALLBACK_MODELS` (vazio: `claude-opus-5` para o Opus 5.5; `none` desliga). O SDK não repete (`max_retries=0`): o retry é do consumidor (AC-004-09).
- **Ollama:** `/api/chat` em NDJSON sobre `httpx2`; `OLLAMA_HOST` (só http/https, sem credenciais) e `OLLAMA_MODEL`. Custo 0; a contagem de tokens é uma estimativa por excesso.
- **Erros:** `ProviderUnavailableError` (transitório: 408, 409, 429, 5xx, 529, ligação ou timeout, também a meio do stream, ou um erro `overloaded`/`api_error` dentro do SSE) e `ProviderError` (permanente: restantes 4xx, SSE malformado). Nunca levam a mensagem do fornecedor.
- **Custos (`pricing/2026-11-23.json`):** USD por milhão de tokens, da página oficial de preços (consultada a 2026-11-23). Mudar um preço é um ficheiro novo. O custo soma as tentativas (`usage.iterations`) ao preço de cada modelo e arredonda para cima a 8 casas (`decimal_usd`). O tecto antes da chamada **soma a cadeia inteira** (modelo e fallbacks), porque cada tentativa é facturada.
- **Logs:** em DEBUG, o SDK regista o corpo do pedido (prompts). O `configure_logging` mantém o `anthropic` e o `httpx2`/`httpcore2` no mínimo em WARNING, e há um teste-canário que o prova.

- **Consumo parcial:** o `stream` aceita um `UsageMeter`, que o adaptador actualiza à medida que o fornecedor reporta tokens. Depois de um timeout, de um cancelamento ou de um erro a meio, o consumidor lê `meter.snapshot()` e regista o que já foi facturado (AC-004-06).
- **Prazos:** `timeout_seconds` é um prazo total do stream, verificado a cada evento: um fornecedor que pinga devagar não estica o turno. O prazo do turno, contado desde a recepção da mensagem, é do consumidor (E3.4).
- **Retry:** cada erro leva `after_first_delta`. Depois do primeiro delta não se repete, nem num erro transitório (AC-004-09).
- **Modelo:** o adaptador recusa (`model_not_allowed`) um pedido cujo modelo não seja o configurado, antes de qualquer chamada.
- **Erros:** levantados sem a excepção original encadeada (`__context__`), que guardava o pedido (com a chave no cabeçalho) e o corpo do fornecedor. Os frames do traceback continuam a ter variáveis locais com o prompt: nenhum exportador de erros pode capturar variáveis locais (E7.1).
- **Saída de rede:** os clientes HTTP ignoram proxies e certificados do ambiente (`trust_env=False`). O Ollama não segue redirects, e só aceita `http` em claro dentro da máquina ou da rede local (localhost, `host.docker.internal`, nomes do Compose, IPs privados); fora dela, `https`.
- **Spans do SDK desligados** (`open_telemetry=False`): no modo `content`, o SDK põe prompts e respostas nos spans. Os spans do KAI entram na E7.1, só com metadados.
- **Preço desconhecido depois da chamada:** se um modelo não tiver preço ou houver um modificador fora da tabela (geografia, fast mode, cache de 1 h), `cost()` falha. Nesse caso o consumidor regista `cost_conservative()`, que nunca subestima.

**[P] Risco aceite em dev (revisão de segurança da E3.3):**
- as redes do `ai-engine` não são `internal`, por isso o serviço tem saída livre para a internet (precisa dela para a Anthropic);
- a `ANTHROPIC_API_KEY` vai no `environment`, visível com `docker inspect`.
- Reavaliar (Docker secrets, proxy de saída) quando chegarem as ferramentas com acesso à rede.

O consumidor (E3.4) e o cancelamento (E3.5) vêm a seguir.

## Correr

O serviço está no profile `messaging` do Compose, porque precisa do RabbitMQ, do seu Redis e das passwords `KAI_RABBITMQ_AI_ENGINE_PASSWORD` e `KAI_AI_ENGINE_REDIS_PASSWORD` (geradas com `scripts/dev/passwords.sh`, ver [`rabbitmq.md`](../../docs/engineering/rabbitmq.md)):

```bash
docker compose --profile messaging up -d --wait ai-engine
```

Não tem porta publicada no host (ADR-0010): só se chega a ele em `http://ai-engine:8000`, a partir das redes `messaging` e `telemetry`. Está também na rede interna `ai-engine-data`, só com o seu Redis.

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
scripts/ci/integration.sh   # serviço real contra o RabbitMQ e o Redis da stack kai-it
```

Os testes de `tests/integration/` só correm no `integration.sh` (cenários `base`, `budget`, `retry` e `slow`, com o fake configurado por `KAI_FAKE_*`); na CI unitária ficam ignorados.

## Dependências (P-021)

- **Declaração:** as versões exactas estão em `requirements.in` (runtime) e `requirements-dev.in` (CI).
- **Locks:** `requirements.txt` e `requirements-dev.txt` têm todas as transitivas com hashes, e a imagem instala-as com `pip install --require-hashes --no-deps`.
- **Regenerar os locks:** `scripts/dev/ai-engine-lock.sh <AAAA-MM-DD>`, em que a data limite de publicação é 14 dias antes do dia em que o corres. O `uv` 0.13.7 serve só para gerar os locks, num contentor descartável.
- **Dependência nova:** pede a aprovação do owner e a verificação da licença.

**Terceira lista (E3.4a, aprovada pelo owner com o plano):** `redis` 8.1.0 (MIT, sem transitivas no Python 3.14); `jsonschema` 4.26.0 passa de dev a runtime, com as transitivas que já estavam no lock (`attrs`, `jsonschema-specifications`, `referencing`, `rpds-py`). O `pytest-asyncio` deixou de ser preciso.

**Licenças (verificadas no PyPI a 2026-11-23):** MIT, BSD-2/3, Apache-2.0 (incluindo o SDK `anthropic` 2.6.0), PSF-2.0 e MPL-2.0 (`certifi`, `pathspec`, usadas sem modificações). Todas são compatíveis com a Apache-2.0 do KAI.

**[P] Aviso conhecido:** o Starlette 1.10 avisa que o `TestClient` sobre o `httpx` está obsoleto e recomenda o `httpx2`. Reavaliar quando subirmos o FastAPI ou o Starlette.
