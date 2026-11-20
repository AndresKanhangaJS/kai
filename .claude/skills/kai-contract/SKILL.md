---
name: kai-contract
description: Define ou altera contratos entre Laravel e Python. Cobre OpenAPI 3.1 para REST, AsyncAPI 3.x + JSON Schema para comandos e eventos RabbitMQ, envelope de mensagem, versionamento, regras de compatibilidade e testes de contrato. Usa antes de implementar qualquer endpoint interno, mensagem de fila ou mudança de payload, ou quando o owner disser "contrato", "schema do evento", "OpenAPI", "AsyncAPI", "nova mensagem", "breaking change".
---
# kai-contract: contratos Laravel ↔ Python

Regras de base: `.claude/rules/contracts.md`, ADR-0002 e ADR-0003. Catálogo inicial de mensagens: `docs/product/analysis.md` §5.5.

## Estrutura (criada no M02, não antes)
```
packages/contracts/
  openapi/internal-v1.yaml          # REST interno (tool-authorizations, health, retrieval)
  asyncapi/kai-v1.yaml              # canais kai.commands / kai.events
  schemas/envelope.v1.json          # envelope comum
  schemas/<tipo>.v<major>.json      # payload por mensagem
  examples/<tipo>/valid/*.json      # exemplos válidos
  examples/<tipo>/invalid/*.json    # exemplos que devem falhar
  CHANGELOG.md
```

## Procedimento: nova mensagem ou endpoint
1. Confirma na spec que existe um critério de aceitação que precisa do contrato.
2. Nome: `<contexto>.<entidade>.<acção>.v<major>`. Comando (imperativo, `requested`) ou evento (passado, `completed`, `failed`).
3. Payload em JSON Schema (draft 2020-12, ou a versão suportada pelo AsyncAPI escolhido):
   - `additionalProperties: false`;
   - `required` explícito;
   - limites (`maxLength`, `enum`, `format`);
   - sem segredos;
   - IDs em vez de conteúdo sensível.
4. Envelope (`schemas/envelope.v1.json`):
   - `id` (UUIDv7), `type`, `occurred_at`, `correlation_id`, `causation_id`, `idempotency_key`, `producer`, `traceparent`, `payload`.
5. Define a chave de idempotência de negócio, por exemplo:
   - `turn:{user_message_id}`
   - `toolexec:{mission_step_id}`
6. Escreve pelo menos 2 exemplos válidos e 2 inválidos (campo extra, campo obrigatório em falta).
7. Regista o contrato em `asyncapi/kai-v1.yaml` ou `openapi/internal-v1.yaml` e no `CHANGELOG.md`.
8. Testes de contrato:
   - **Produtor:** gera a mensagem a partir do domínio e valida-a contra o schema.
   - **Consumidor:** lê todos os exemplos válidos e rejeita todos os inválidos.
   - **CI:** os dois lados correm sobre os mesmos ficheiros de `examples/`.
9. Pede aprovação ao owner: uma alteração de contrato é sempre um ponto de paragem.

## Compatibilidade
| Alteração | Classificação | Acção |
|---|---|---|
| Campo opcional novo | Compatível | Mesma major; nota no CHANGELOG |
| Campo obrigatório novo, remover ou renomear um campo, mudar o tipo | **Incompatível** | Nova major `.v2`, publicada em paralelo durante ≥ 1 milestone; data de fim da v1 |
| Novo valor de `enum` | Compatível só se os consumidores tolerarem valores desconhecidos | Verificar os consumidores primeiro |

## Saída
- Os ficheiros do contrato, os exemplos, o CHANGELOG e o resumo da classificação de compatibilidade.
