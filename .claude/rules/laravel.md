---
paths:
  - "apps/api/**"
---
# Laravel Core (`apps/api`)

Baseline: Laravel 13, PHP 8.5 (ADR-0007). Modular monolith: ADR-0001.

## Módulos
- Um módulo por bounded context (`analysis.md` §5.1).
- Um módulo não acede às tabelas de outro módulo; comunica por serviços de aplicação ou eventos internos.
- Testes de arquitectura (Pest arch) garantem as fronteiras entre módulos e a proibição de `DB::` fora da camada de infraestrutura.
- O Laravel é o único escritor de missões, aprovações, auditoria e memórias; só ele muda o estado de uma missão.

## Política e segurança
- O Policy Decision Point vive aqui. O *execution grant* é um JWS assimétrico, ≤ 60 s, `jti` de uso único, com `aud` = ai-engine (ADR-0010).
- Cada endpoint autentica e verifica o dono do recurso (`user_id`) explicitamente, nunca por omissão.
- `audit_logs` é append-only: só inserts, nunca updates nem deletes.

## Dados e mensagens
- Migrations reversíveis e expand/contract (skill `kai-db-migration`).
- Eventos entre serviços: escreve na tabela `outbox` na mesma transacção; um relay publica no RabbitMQ com publisher confirms.
- Entre linguagens nunca vai o payload serializado de jobs Laravel; vai JSON validado contra `packages/contracts`.
- Consumidores idempotentes, com inbox (`processed_message_id`).

## Qualidade
- Pest para os testes; PHPStan/Larastan no nível 6, sem baseline (ADR-0014).
- Erros e logs estruturados com `trace_id`, sem PII nem segredos.
- Comandos: `scripts/ci/api.sh` (Pint `--test`, PHPStan/Larastan nível 6 sem baseline, Pest). Ver `docs/engineering/ci.md` e ADR-0014.
