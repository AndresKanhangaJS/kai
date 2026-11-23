# Spike M03 E1.1: Reverb com publicação a partir de Python

**Pergunta (condição do ADR-0009):** o Reverb aceita publicação HTTP (protocolo Pusher) de um cliente não-Laravel e entrega-a por ordem, com latência baixa, num canal privado?

**Resposta: sim** (2026-11-23). Decisão registada no [ADR-0015](../../docs/adr/0015-streaming-de-tokens-reverb-confirmado.md).

## Como correr

```bash
docker compose up -d            # stack de dev, com o serviço reverb
spikes/m03-reverb/run.sh        # 100 deltas a cada 50 ms
SPIKE_COUNT=500 SPIKE_INTERVAL_MS=10 spikes/m03-reverb/run.sh
```

| Ficheiro | O quê |
|---|---|
| `publish.py` | Python 3.14, só a biblioteca padrão: `POST /apps/{id}/events` assinado (HMAC-SHA256); negativo com assinatura errada |
| `subscribe.mjs` | Node 24, `WebSocket` nativo, protocolo Pusher 7: subscreve `private-run.{id}`, mede ordem e latência; negativos de auth e de origem |
| `compose.spike.yml` | Serviços descartáveis (perfil `spike`), imagens fixadas por digest, credenciais pela mesma interpolação do Compose |
| `run.sh` | Orquestra: subscritor, publicador, resultado (exit 0 só se o critério for cumprido) |

## Resultados

| Corrida | Recebidos | Por ordem | p50 / p95 / máx. |
|---|---|---|---|
| 100 × 50 ms | 100/100 | sim | 5,8 / 8,9 / 16,2 ms |
| 500 × 10 ms | 500/500 | sim | 5,8 / 8,1 / 48,3 ms |

Negativos recusados:
- publicação mal assinada → 401;
- subscrição com auth inválida → `4009 Connection is unauthorized`;
- origem `evil.example` → `4009 Origin not allowed`.

Os logs do Reverb não têm o conteúdo dos deltas nem o segredo.

## Limites do spike
- **A assinatura da subscrição é calculada no próprio script.** No produto, quem a emite é o Laravel em `/broadcasting/auth`, depois de verificar o dono do run (E4.6).
- **A latência mede o transporte (Python → Reverb → cliente) em local.** O TTFT do LLM e a latência de ponta a ponta medem-se na E7.
- **Este directório é descartável.** Sai quando o AI Engine publicar os deltas a sério (E3.4) e o E2E do AC-03 cobrir o caminho (E5.1).
