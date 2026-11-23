# ADR-0009: Streaming de tokens por Reverb

- **Estado:** Substituído por ADR-0015
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.6, p.7; ADR-0002, 0003; FR-008; AC-03

## Contexto
- O PDF exige respostas em streaming [C p.6] e põe Reverb/WebSockets no gateway Laravel [C p.7].
- O LLM é chamado pelo Python. O caminho dos tokens até ao cliente não está definido (A-07).

## Opções consideradas
1. **Python publica deltas num canal privado do Reverb, autorizado pelo Laravel.** Um único canal para tokens, progresso e aprovações; aguenta reconexões. Contra: mais saltos; a ordem tem de ser garantida (`seq`).
2. **SSE do Python, reencaminhado pelo Laravel.** Simples. Contra: prende um worker PHP por stream e o cancelamento atravessa dois saltos.
3. **Cliente ligado directamente ao Python, com token.** Menor latência. Contra: uma segunda superfície pública com autenticação duplicada.

## Decisão
- **Opção 1.** Deltas agregados (~50 ms, com `seq`) no canal `run.{id}`.
- A resposta final chega pelo evento `ai.conversation.turn.completed.v1`; o Laravel persiste-a e o cliente reconcilia.
- Os deltas são efémeros e não passam pelo RabbitMQ.
- **Condição:** um spike no M03 confirma que o Reverb aceita publicação HTTP (protocolo Pusher) a partir de um cliente não-Laravel. Se falhar, a solução passa a ser a opção 2.

## Consequências
- **Positivas:** uma só via de tempo real para a UI; o gateway continua a ser a única superfície pública.
- **Negativas:** o caminho tem mais peças; o TTFT tem de ser medido (NFR-015).

## Verificação
- Spike com medição do TTFT.
- E2E do AC-03.
