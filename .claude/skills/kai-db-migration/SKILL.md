---
name: kai-db-migration
description: Escreve ou revê migrações MySQL 8.4 seguras para o Laravel do KAI. Cobre reversibilidade, expand/contract para evitar downtime, idempotência, índices, tabelas outbox e inbox, isolamento por user_id e dados de teste sintéticos. Usa ao criar ou alterar tabelas, colunas, índices ou dados persistentes, ou quando o owner disser "migração", "migration", "nova tabela", "alterar coluna", "schema da BD".
---
# kai-db-migration: migrações MySQL seguras

Base: MySQL 8.4 LTS (ADR-0007); o Laravel é o único escritor das suas tabelas (ADR-0002); PDF p.11 (entidades) e p.17 (migrations controladas e rollback).

## Checklist por migração
1. **Propósito:** liga a migração a uma spec ou critério; uma intenção por migração.
2. **Reversível:**
   - `down()` funcional e testado;
   - se a reversão perder dados, diz-o explicitamente e pede aprovação.
3. **Expand/contract** para alterações em tabelas com dados:
   - **Expand:** adiciona colunas ou tabelas novas nullable ou com default, e escreve nos dois formatos.
   - **Migrate:** backfill em lotes pequenos e idempotente (com `WHERE` que pode ser repetido), fora da migração de schema.
   - **Contract:** remove o antigo numa release seguinte, depois de verificado.
   - Nunca renomeies nem removas uma coluna em uso no mesmo deploy em que o código deixa de a usar.
4. **Locks:**
   - prefere operações *online* do InnoDB;
   - evita `ALTER` que reconstrói tabelas grandes sem necessidade;
   - indica o algoritmo esperado quando for relevante.
5. **Integridade:**
   - chaves estrangeiras dentro do mesmo módulo; entre módulos, só o ID, sem FK;
   - `NOT NULL` e defaults explícitos;
   - `utf8mb4` / `utf8mb4_0900_ai_ci`.
6. **Isolamento:**
   - tabelas com dados próprios têm `user_id` indexado (índice composto com a chave de acesso mais comum);
   - nenhuma query de aplicação sem filtro de dono.
7. **Índices:** um por padrão de acesso real (cita a query); evita duplicados e índices em colunas de baixa cardinalidade.
8. **IDs:** UUIDv7 (ordenáveis) para entidades expostas ou mensagens; nunca IDs sequenciais expostos sem necessidade.
9. **Append-only:**
   - em `audit_logs` e `mission_events`, sem `updated_at`;
   - a aplicação não emite UPDATE nem DELETE nestas tabelas; se possível, o utilizador da BD não tem essas permissões.
10. **Outbox:**
    - colunas `id`, `type`, `payload` (JSON), `traceparent`, `tracestate`, `occurred_at`, `published_at` nullable, `attempts`;
    - índice em (`published_at`, `occurred_at`).
11. **Inbox:** `message_id` como PK (dedupe) e `processed_at`.
12. **Dados pessoais:** marca colunas com PII no docblock da migração e confirma a retenção e a eliminação (NFR-010).
13. **Seeds e factories:** só dados sintéticos; nunca dumps de produção.
14. **Testes:**
    - `migrate` → `rollback` → `migrate` numa BD limpa;
    - um teste de integração por constraint relevante.

## Saída
A migração, o seed ou factory sintético se for preciso, os testes, e uma nota de deploy: ordem expand/migrate/contract, impacto de locks, plano de rollback.
