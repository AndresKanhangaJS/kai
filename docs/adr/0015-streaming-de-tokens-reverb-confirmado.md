# ADR-0015: Streaming de tokens por Reverb, confirmado pelo spike

- **Estado:** Aceite (2026-11-23)
- **Data:** 2026-11-23
- **Decisores:** owner
- **Relacionados:** substitui o ADR-0009; FR-008; NFR-015; AC-03; M03 E1.1/E1.4; ADR-0002, ADR-0010

## Contexto
- [C ADR-0009] O streaming por Reverb foi aceite **com uma condição**: um spike no M03 tinha de confirmar que o Reverb aceita publicação HTTP (protocolo Pusher) a partir de um cliente não-Laravel. Se falhasse, passava a SSE através do Laravel.
- [C, spike de 2026-11-23, `spikes/m03-reverb/`]:
  - `laravel/reverb` v1.13.0 corre como serviço próprio no Compose, na imagem do api (precisou da extensão `pcntl`).
  - Um script Python só com a biblioteca padrão publica por `POST /apps/{id}/events`, assinado com HMAC-SHA256.
  - Um cliente WebSocket (Node 24, protocolo Pusher 7) recebe os eventos num canal privado.

| Corrida | Recebidos | Por ordem | Latência p50 / p95 / máx. |
|---|---|---|---|
| 100 deltas, a cada 50 ms | 100/100 | sim | 5,8 / 8,9 / 16,2 ms |
| 500 deltas, a cada 10 ms | 500/500 | sim | 5,8 / 8,1 / 48,3 ms |

- [C, mesmo spike] Os negativos são recusados:
  - publicação mal assinada → HTTP 401;
  - subscrição com auth inválida → `4009 Connection is unauthorized`;
  - origem não permitida → `4009 Origin not allowed`.
- [C] Os logs do Reverb não têm o conteúdo dos deltas nem o segredo.

## Opções consideradas
1. **Manter o Reverb (a opção 1 do ADR-0009), agora sem condição.** O critério do spike foi cumprido com folga (p95 < 100 ms).
2. **Passar a SSE através do Laravel (fallback).** Já não se justifica: prende um worker PHP por stream e o cancelamento atravessa dois saltos.

## Decisão
O streaming usa o Reverb, sem condição. O AI Engine publica deltas agregados (cerca de 50 ms, com `seq`) no canal privado `private-run.{run_id}` pela API HTTP do protocolo Pusher. Usa só a biblioteca padrão (HMAC-SHA256), por isso não há SDK novo no Python. Mantém-se o resto do ADR-0009:
- os deltas são efémeros e não passam pelo RabbitMQ;
- a resposta final chega em `ai.conversation.turn.completed.v1`, e o cliente reconcilia por `delta_count`;
- só o dono do run subscreve o canal: o Laravel decide em `/broadcasting/auth` (E4.6).

Configuração:
- **Servidor:** serviço `reverb` só em `127.0.0.1:8080`. `allowed_origins` deriva do `FRONTEND_URL` e nunca é `*`.
- **Credenciais:** o segredo da app vem do ambiente. Em dev, se faltar, o Compose usa um valor de exemplo público (`changeme-local-reverb`). Fora de `local`/`testing`, o Laravel recusa arrancar com esse valor ou sem segredo (`AppServiceProvider::ensureSafeReverbSecret`, testado).
- **Endurecimento** (revisão de segurança do spike):
  - client events desligados (`accept_client_events_from = none`; um `client-*` recebe `4301`);
  - rate limiting ligado, com a ligação terminada ao atingir o limite;
  - `max_connections` a 100;
  - os testes correm com o broadcaster `null` (`scripts/ci/api.sh`, testado).

## Consequências
- **Positivas:**
  - o gateway continua a ser a única superfície pública;
  - a latência do transporte (cerca de 9 ms p95 em local) é desprezável face ao TTFT do LLM;
  - zero dependências novas no Python.
- **Negativas / custos:**
  - mais um contentor, e mais uma porta que o E2E tem de ter livre (8080);
  - mais 13 pacotes PHP de runtime (`laravel/reverb` e dependências, MIT);
  - o segredo da app passa a ser partilhado entre o api, o reverb e o AI Engine.
- **Riscos e mitigação:**
  - **Origem só por host:** o Reverb compara só o host (`localhost`), não a porta. Aceite em dev; em produção o host é dedicado (M10).
  - **Tamanho dos eventos:** `max_request_size` vem a 10 000 bytes por omissão, o que obriga a agregar deltas sem os tornar enormes. Se for preciso, ajusta-se por variável de ambiente.
  - **Rotação do segredo:** produção gera um valor aleatório e roda-o (M10).
  - **Segredo único com todos os poderes:** o Pusher não tem credenciais por papel. O AI Engine só precisa de publicar, mas o segredo também assina subscrições e lista canais. Se o engine for comprometido, o atacante lê e injecta no stream de todos os runs. **[P] Risco aceite no dev, a decidir pelo owner antes do M10:** aceitar com mitigações (segredo do engine num cofre separado e rotação; o cliente reconcilia sempre pelo `turn.completed` e pelo `delta_count`) ou usar um relay em que só o Laravel tem o segredo (mais um salto).
  - **Replay:** um POST assinado vale 600 s e não tem nonce. O cliente (E5) descarta `seq <= último`. TLS na rede interna, só se se justificar no M10.
  - **`pcntl` na imagem do api:** a extensão também fica disponível no `php -S`. Aceitável em dev; no M10, imagem ou target separado para o reverb.
  - **Origem só por host:** outro servidor em `localhost:<porta>` passa o filtro de origem. Na E4.6 entra um teste negativo de `/broadcasting/auth` a partir de outra origem `localhost`.
  - **Canais públicos não exigem auth:** todo o evento do KAI usa `PrivateChannel` (teste de arquitectura na E4.6).

## Verificação
- `spikes/m03-reverb/run.sh` repete a medição e os negativos, incluindo o client event recusado (exit 0 só se 100 % por ordem e p95 < 100 ms).
- `tests/Feature/BroadcastingConfigTest.php`: broadcaster `null` nos testes; client events desligados; segredo de exemplo recusado fora de `local`/`testing`.
- E4.6: testes negativos de `/broadcasting/auth` (outro dono, sessão revogada).
- E5.1: E2E do AC-03 com tokens incrementais. O TTFT de ponta a ponta (NFR-015) mede-se na E7.

## Fontes
- Packagist: `laravel/reverb` v1.13.0 (2026-10-19, MIT); a v1.14.0 (2026-11-16) tinha menos de 2 semanas. As 13 dependências novas são MIT. Verificado em 2026-11-23.
- Protocolo Pusher (API HTTP de eventos com `auth_signature` HMAC-SHA256; WebSocket protocolo 7): documentação oficial do Pusher Channels, implementada pelo Reverb.
