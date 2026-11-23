---
paths:
  - "packages/contracts/**"
---
# Contratos (`packages/contracts`)

Fronteira Laravel ↔ Python: ADR-0002. Mensageria: ADR-0018 (substitui o ADR-0003). Skill: `kai-contract`.

- REST síncrono: OpenAPI 3.1. Eventos e comandos RabbitMQ: AsyncAPI 3.x com payloads em JSON Schema.
- O contrato muda **antes** do código e no mesmo PR que os testes dos dois lados.
- Nomes: `<contexto>.<entidade>.<acção>.v<major>` (ex.: `ai.conversation.turn.requested.v1`).
- Envelope obrigatório: `id` (UUIDv7), `type`, `occurred_at`, `correlation_id`, `causation_id`, `idempotency_key`, `producer`, `traceparent`.
- Payloads com `additionalProperties: false` e campos com formatos e limites (`maxLength`, `enum`).

## Compatibilidade
- Dentro de uma major, só alterações aditivas (campos opcionais novos); os consumidores são *tolerant readers*.
- Alteração incompatível: nova major publicada em paralelo durante pelo menos um milestone, com o fim de vida no `CHANGELOG`.
- Nunca reutilizes um nome de campo com outro significado.

## Verificação
- Cada schema tem exemplos válidos e inválidos versionados, validados na CI.
- Testes de contrato: o produtor gera exemplos e o consumidor do outro lado valida-os.
- Nada de segredos, tokens ou PII em exemplos ou fixtures; os dados são sintéticos.
- Uma alteração de contrato pede a aprovação do owner (ver "Quando parar e perguntar").
