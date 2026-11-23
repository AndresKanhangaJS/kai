# AI Engine (`apps/ai-engine`)

Serviço Python 3.14 + FastAPI do KAI. Recebe turnos de conversa pelo RabbitMQ, chama o modelo através do `LLMGateway`, envia os deltas pelo Reverb e reporta o resultado em eventos. Não decide nem persiste estado de negócio: isso é do Laravel (ADR-0002).

- **Spec:** [SPEC-004](../../docs/specs/004-ai-engine-m03.md).
- **Contratos:** [`packages/contracts`](../../packages/contracts/README.md).
- **ADRs:** 0006 (LLM), 0010 (rede privada), 0015 (Reverb), 0016 (`aio-pika`), 0017 (OpenTelemetry), 0018 (retry e DLQ).
- **Regras:** [`.claude/rules/python-ai-engine.md`](../../.claude/rules/python-ai-engine.md).

## Estado (M03 E3.3)

Endpoints de health, conforme o `health.v1`:
- `GET /health/live`;
- `GET /health/ready`, que dá 200 só com a ligação ao RabbitMQ activa e 503 caso contrário.

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

**Licenças (verificadas no PyPI a 2026-11-23):** MIT, BSD-2/3, Apache-2.0 (incluindo o SDK `anthropic` 2.6.0), PSF-2.0 e MPL-2.0 (`certifi`, `pathspec`, usadas sem modificações). Todas são compatíveis com a Apache-2.0 do KAI.

**[P] Aviso conhecido:** o Starlette 1.10 avisa que o `TestClient` sobre o `httpx` está obsoleto e recomenda o `httpx2`. Reavaliar quando subirmos o FastAPI ou o Starlette.
