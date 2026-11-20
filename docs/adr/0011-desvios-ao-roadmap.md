# ADR-0011: Desvios ao roadmap do PDF

- **Estado:** Aceite (2026-11-20, D-11)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.17–18, p.21; ADR-0003; `docs/product/analysis.md` §7

## Contexto
O roadmap do PDF [C p.17–18] coloca:
- o RabbitMQ no M07;
- o Outbox, a DLQ e a idempotência no M09;
- a observabilidade e o CI/CD no M10.

Isto entra em conflito com:
- "instrumentar os serviços desde o início" [C p.5];
- a Definition of Done, que exige testes que passam e revisão antes de integrar [C p.21];
- a indexação idempotente no M04 [C p.11];
- o MVP, que atravessa React → Laravel → RabbitMQ → Python (D-10).

## Opções consideradas
1. **Antecipar o mínimo.** Mantém os princípios; a fatia vertical é real desde o início.
2. **Seguir o PDF à letra.** Contradiz os princípios da p.5 e a DoD.
3. **Antecipar só a CI.** Meio-termo, mas sem trace de ponta a ponta no MVP.

## Decisão
**Opção 1:**
- **M02:** CI com lint, análise estática, testes, validação de contratos e secret scanning.
- **M03:** RabbitMQ com Outbox, Inbox e DLQ mínimos; OpenTelemetry com o contentor `grafana/otel-lgtm`.
- **M10 (como no PDF):** CD, publicação de imagens, SBOM, scan de imagens e a stack de observabilidade separada.
- **M09:** o endurecimento do Outbox e da DLQ e as extracções de serviços.

## Consequências
- **Positivas:** qualidade e rastreabilidade desde o primeiro código; o MVP demonstra a arquitectura real.
- **Negativas:** M02 e M03 ficam mais pesados; mais um contentor (`otel-lgtm`) em desenvolvimento.

## Verificação
- CI verde como critério de aceitação do M02.
- Trace de ponta a ponta (AC-08) como critério do M03.
