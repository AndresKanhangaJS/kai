# ADR-0016: Clientes AMQP: php-amqplib no Laravel e aio-pika no AI Engine

- **Estado:** Proposto
- **Data:** 2026-11-23
- **Decisores:** owner
- **Relacionados:** P-019; ADR-0003 (outbox e inbox), ADR-0007 (RabbitMQ 4.4), ADR-0015; M03 E1.2, E2.1, E3.4, E4.4

## Contexto
- [C ADR-0003] O Laravel publica a partir do outbox com *publisher confirms*. As duas pontas consomem com inbox, quorum queues e DLX.
- [C ADR-0007] Python 3.14 com FastAPI (asyncio) e PHP 8.5.
- [C security.md] Uma dependência nova pede a aprovação do owner, a licença verificada, a versão fixa e, por regra do projecto, pelo menos 2 semanas desde a publicação.
- [C, Packagist, PyPI e PECL, 2026-11-23]:

| Lado | Candidato | Versão (data) | Licença | Notas |
|---|---|---|---|---|
| PHP | `php-amqplib/php-amqplib` | 3.7.5 (2026-09-28) | **LGPL-2.1-or-later** | 145 M downloads, 3,2 M por mês. Síncrono; exige `ext-sockets` e traz `phpseclib/phpseclib` (MIT, novo) |
| PHP | PECL `amqp` | 2.2.0 (2026-01-02) | PHP License 3.01 | Extensão C sobre a `librabbitmq` (pacote de sistema); compilada na imagem, sem lock do Composer |
| PHP | `bunny/bunny` | 0.5.6 (2025-05-22) | MIT | **Excluído:** exige `react/promise ~2.2`, e o Reverb já fixou a v3.3.0 (conflito); sem releases há 18 meses |
| Python | `aio-pika` | 10.2.3 (2026-11-08) | Apache-2.0 | asyncio, reconexão robusta, instrumentação OTel oficial. Traz `aiormq` 7.2.5 e `pamqp` 5 |
| Python | `aiormq` | 7.2.5 (2026-11-01) | Apache-2.0 | É a camada de baixo do `aio-pika`; API mais crua |
| Python | `pika` | 1.4.4 (2026-08-06) | BSD-3-Clause | Síncrono por omissão; obriga a threads com o FastAPI. A 1.5.0 tem menos de 2 semanas |

## Opções consideradas
1. **`php-amqplib` mais `aio-pika`.** É o par mais usado e mais simples de operar. Contra: a LGPL no lado PHP.
2. **PECL `amqp` mais `aio-pika`.** A licença é permissiva. Contra: a extensão C e a `librabbitmq` saem do lock do Composer, o build da imagem fica mais pesado e a extensão é menos usada.
3. **`aiormq` ou `pika` no Python.** Mais baixo nível (`aiormq`), ou síncrono (`pika`); nenhum dos dois traz vantagem sobre o `aio-pika`.

## Decisão
- **Laravel:** `php-amqplib/php-amqplib` 3.7.5, usado só no relay do outbox e no consumidor de eventos (camada de infraestrutura), atrás de uma interface própria; a imagem do api ganha `ext-sockets`.
- **AI Engine:** `aio-pika` 10.2.3, com `publisher_confirms` e `prefetch_count` explícitos.
- **[P] Licença:** a LGPL-2.1 é compatível com a Apache-2.0 do KAI (D-02) quando a biblioteca é usada sem alterações e fica substituível (instalada pelo Composer, não copiada para o repositório). **O owner confirma que aceita a LGPL;** se não aceitar, fica a opção 2.

## Consequências
- **Positivas:** clientes maduros, com *publisher confirms* e argumentos de fila (quorum, DLX, TTL); nenhum conflito com o lock actual.
- **Negativas / custos:** uma dependência LGPL e uma transitiva nova (`phpseclib`); mais uma extensão na imagem do api; as transitivas Python (`aiormq`, `pamqp`, `yarl`, `multidict`, `propcache`, `idna`) têm a licença verificada quando entram, na E3.2.
- **Riscos e mitigação:** o cliente PHP é síncrono, o que chega para um relay e um consumidor em processos próprios. A interface interna permite trocar de cliente sem tocar no domínio.

## Verificação
- E2.1: teste de integração contra o RabbitMQ real (publisher confirm recebido, quorum queue, mensagem rejeitada vai para a DLQ).
- E4.4: matar o relay a meio não perde nem duplica.
- Lockfiles com hashes (`composer.lock`, `requirements.lock`); licenças listadas no PR.

## Fontes
- Packagist (`php-amqplib/php-amqplib`, `bunny/bunny`), PyPI (`aio-pika`, `aiormq`, `pika`) e PECL (`amqp`): versões, datas, licenças e `require`, consultados a 2026-11-23.
