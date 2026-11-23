# ADR-0018: Mensageria com RabbitMQ + Outbox/Inbox, com retry no consumidor

- **Estado:** Aceite (2026-11-23, decisão do owner sobre o achado N1 da revisão da E2.1)
- **Data:** 2026-11-23
- **Decisores:** owner
- **Relacionados:** substitui o ADR-0003; PDF p.5, p.7, p.11, p.15, p.18; ADR-0002, 0011, 0016; D-11; M03 E2.1

## Contexto
- [C ADR-0003] RabbitMQ 4.4 com outbox e inbox, quorum queues e DLX. O ADR-0003 previa também "filas de retry com TTL, backoff e jitter" [C p.15].
- [C, M03 E2.1, 2026-11-23] Implementámos o retry pelo broker (principal → DLX → fila de retry com TTL → principal), para os serviços não poderem republicar na própria fila (revisão de segurança, achado 2). O resultado foi uma perda de mensagens, **confirmada no broker real**: uma mensagem que faz o consumidor rebentar antes do `ack` é entregue 6 vezes (`x-delivery-limit` 5), vai para o retry e, quando o TTL expira, desaparece (0 na principal, no retry e na DLQ). A detecção de ciclos de dead-letter do RabbitMQ descarta-a, porque a mensagem volta à mesma fila sem nenhuma rejeição pelo caminho.
- Com o retry por republicação no consumidor, a perda desaparece, mas reabre o achado 2. Além disso, é incompatível com a validação do `user_id` AMQP (a cópia levaria o `user_id` do consumidor).

## Opções consideradas
1. **Retry no consumidor, sem filas de retry.** Em memória, com backoff e jitter; depois, `nack` → DLQ pelo broker. Nenhuma perda, nenhum serviço escreve no retry nem na DLQ. Contra: a mensagem em espera ocupa um slot do prefetch.
2. **Filas de retry com republicação pelo consumidor.** Mantém o texto do ADR-0003, mas reabre a falsificação de mensagens na própria fila.
3. **Retry pelo broker, com o consumidor a contar o `x-death` e a enviar para a DLQ.** Exige escrita na DLQ própria; é a mais complexa e a mais frágil.

## Decisão
Mantém-se tudo o que o ADR-0003 decidiu, **excepto o retry**, que passa a ser o seguinte:
- **RabbitMQ 4.4:** exchanges `kai.commands` e `kai.events` (topic), uma quorum queue duradoura e limitada por consumidor e uma DLQ por consumidor, alimentada só pelo broker (DLX). **Não há filas de retry.**
- **Falha transitória:** o consumidor repete em memória, com backoff exponencial e jitter (por omissão 3 tentativas, com um tecto de cerca de 30 s no total), sem fazer `ack`.
- **Falha que persiste ou permanente** (schema inválido, `user_id` ou dono divergente): `nack` sem requeue → DLX → DLQ.
- **Crash antes do `ack`:** ao fim de 5 entregas (`x-delivery-limit`), o broker manda a mensagem para a DLQ.
- **Reprocessar uma DLQ** nunca é mover mensagens para a fila principal. O produtor reemite a partir do outbox ou da auditoria, como mensagem nova.
- **Sem alterações:**
  - outbox na transacção de negócio, com relay e publisher confirms;
  - inbox nos consumidores (at-least-once);
  - `traceparent` nos headers;
  - entra no M03;
  - os jobs internos do Laravel não usam o RabbitMQ.

## Consequências
- **Positivas:** nenhuma perda (testada); os serviços só escrevem na sua exchange de saída e nunca na DLQ; menos filas.
- **Negativas / custos:** o tempo máximo de retry fica limitado pelo prefetch e pelo `consumer_timeout`; falhas transitórias longas (minutos) acabam na DLQ e são reemitidas pelo produtor, em vez de ficarem à espera no broker.

## Verificação
- `scripts/ci/integration.sh`: um `nack` vai para a DLQ; 6 entregas sem `ack` vão para a DLQ com `x-death` `delivery_limit`; um serviço que tente escrever na DLQ recebe 403.
- Teste de integração: um restart do broker não perde mensagens (NFR-028).
- Teste de idempotência: uma mensagem duplicada não tem efeito duplo.
- Alerta para a DLQ não vazia (E7.2).
