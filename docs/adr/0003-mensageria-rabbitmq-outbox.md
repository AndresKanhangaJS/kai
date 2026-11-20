# ADR-0003: Mensageria com RabbitMQ + Outbox/Inbox

- **Estado:** Aceite (2026-11-20, D-11)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.7, p.11, p.15, p.18; ADR-0002, 0011

## Contexto
- O PDF pede eventos e filas para tarefas assíncronas [C p.5].
- Lista como padrões de resiliência: DLQ, idempotência, retry com backoff e jitter, e Transactional Outbox [C p.15].
- Escrever no MySQL e publicar no broker de forma independente (*dual-write*) perde ou inventa mensagens.
- O roadmap só traz o RabbitMQ no M07 e o Outbox no M09 [C p.18], mas o MVP precisa deles no M03 (D-11).

## Opções consideradas
1. **RabbitMQ 4.4 + Outbox/Inbox.** Maduro, com DLX e quorum queues. Contra: há um relay para operar.
2. **Redis Streams.** Uma peça a menos. Contra: as ferramentas de DLQ e de encaminhamento são mais fracas, e afasta-se do PDF.
3. **Publicação directa sem outbox.** Simples. Contra: o risco de dual-write.

## Decisão
- RabbitMQ 4.4 (ADR-0007): exchanges `kai.commands` e `kai.events` (topic), uma quorum queue duradoura por consumidor, DLX e filas de retry com TTL, backoff e jitter.
- Os produtores escrevem na tabela `outbox` dentro da transacção de negócio; um relay publica com publisher confirms.
- Os consumidores deduplicam com uma tabela inbox e assumem entrega at-least-once.
- `traceparent` vai nos headers AMQP.
- Entra no M03.
- Os jobs internos do Laravel podem usar a fila da BD ou do Redis; o RabbitMQ serve só para mensagens entre serviços.

## Consequências
- **Positivas:** nenhuma mensagem perdida nem fantasma; possibilidade de reprocessar.
- **Negativas:** relay e limpeza do outbox para manter; mais um contentor a partir do M03.

## Verificação
- Teste de integração: restart do broker sem perda (NFR-028).
- Teste de idempotência: mensagem duplicada não tem efeito duplo.
- Alerta quando a DLQ > 0.
