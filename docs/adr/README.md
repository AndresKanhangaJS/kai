# Architecture Decision Records

- Formato: MADR, regras em `ADR-0000`.
- Criar ou substituir: skill `kai-adr`.
- Estados: `Proposto`, `Aceite`, `Rejeitado`, `Obsoleto`, `Substituído por ADR-NNNN`.
- "Aceite" significa decidido pelo owner. Os `Proposto` são revistos no M01.

| ADR | Título | Estado | Data |
|---|---|---|---|
| [0000](0000-registar-decisoes-arquitecturais.md) | Registar decisões arquitecturais (MADR) | Proposto | 2026-11-20 |
| [0001](0001-modular-monolith-e-ai-engine.md) | Modular monolith Laravel + AI Engine Python separado | Proposto | 2026-11-20 |
| [0002](0002-fronteira-de-contratos-laravel-python.md) | Fronteira de contratos Laravel ↔ Python | Proposto | 2026-11-20 |
| [0003](0003-mensageria-rabbitmq-outbox.md) | Mensageria com RabbitMQ + Outbox/Inbox | Aceite | 2026-11-20 |
| [0004](0004-modelo-de-seguranca.md) | Modelo de segurança: o LLM não é fronteira; níveis 1–6 | Substituído por ADR-0013 | 2026-11-20 |
| [0005](0005-memoria-e-rag.md) | Memória e RAG: MySQL, Qdrant e object storage | Proposto | 2026-11-20 |
| [0006](0006-abstraccao-de-llm.md) | Abstracção de LLM como porta própria | Aceite | 2026-11-20 |
| [0007](0007-baseline-de-versoes.md) | Baseline de versões | Aceite | 2026-11-20 |
| [0008](0008-object-storage-seaweedfs.md) | Object storage: SeaweedFS via API S3 | Aceite | 2026-11-20 |
| [0009](0009-streaming-de-tokens-reverb.md) | Streaming de tokens por Reverb | Proposto | 2026-11-20 |
| [0010](0010-autenticacao-entre-servicos.md) | Autenticação entre serviços: JWS assimétrico + rede privada | Aceite | 2026-11-20 |
| [0011](0011-desvios-ao-roadmap.md) | Desvios ao roadmap do PDF | Aceite | 2026-11-20 |
| [0012](0012-idioma-do-repositorio.md) | Idioma do repositório: PT-PT | Aceite | 2026-11-20 |
| [0013](0013-modelo-de-seguranca.md) | Modelo de segurança: o LLM não é fronteira; níveis 1–6 (substitui o ADR-0004) | Aceite | 2026-11-20 |
