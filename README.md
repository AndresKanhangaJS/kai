# KAI — Personal AI Intelligence System

> OBSERVE · LEARN · UNDERSTAND · ANTICIPATE · EXECUTE

O KAI é uma inteligência pessoal que compreende o contexto do utilizador e executa operações autorizadas, mantendo-o sempre informado e no controlo. Liga uma pessoa ao seu conhecimento, ferramentas, aplicações, dados e dispositivos através de linguagem natural, voz e interfaces visuais.

É ao mesmo tempo um produto útil no dia-a-dia e um laboratório público de engenharia de software, AI engineering, sistemas distribuídos, DevOps, segurança e observabilidade.

## Estado

**Product Discovery.** Ainda não existe código de aplicação.

O trabalho feito até agora:
- **Visão do produto:** [`docs/product/kai-vision.md`](docs/product/kai-vision.md); o original é o [PDF](docs/product/1_KAI_Product_Vision_Architecture_Roadmap.pdf).
- **Análise de arquitectura:** requisitos, riscos, bounded contexts, MVP e plano, em [`docs/product/analysis.md`](docs/product/analysis.md).
- **PRD do MVP:** [`docs/product/prd.md`](docs/product/prd.md); spec com os critérios de aceitação em [`docs/specs/001-mvp-fatia-vertical.md`](docs/specs/001-mvp-fatia-vertical.md).
- **Decisões arquitecturais:** em [`docs/adr/`](docs/adr/README.md).
- **Diagramas C4:** contexto e contentores em [`docs/architecture/`](docs/architecture/c4-01-context.md).
- **Identidade visual mínima:** [`docs/product/identidade-visual.md`](docs/product/identidade-visual.md).
- **Ambiente de engenharia para o Claude Code:** [`docs/engineering/claude-code-setup.md`](docs/engineering/claude-code-setup.md).
- **Estado actual:** [`docs/STATUS.md`](docs/STATUS.md).

## Arquitectura (planeada)

- **Core Platform:** Laravel 13 / PHP 8.5, como Modular Monolith. É o sistema de registo e o ponto de decisão de política (ADR-0001, ADR-0002).
- **AI Engine:** Python 3.14 + FastAPI. LLM Gateway (Anthropic + Ollama), contexto, execução de ferramentas com *execution grants* (ADR-0013, ADR-0006).
- **Cliente:** React + TypeScript + Vite, com streaming via Laravel Reverb (ADR-0009).
- **Dados e mensagens:**
  - MySQL 8.4 LTS;
  - RabbitMQ 4.4 com Transactional Outbox (ADR-0003);
  - Redis 8;
  - Qdrant;
  - SeaweedFS via API S3 (ADR-0008).
- **Observabilidade:** OpenTelemetry desde o M03 (ADR-0011).

**Princípio de segurança central:** o modelo de linguagem **não** é uma fronteira de segurança. As permissões são validadas fora do LLM e o conteúdo externo é sempre tratado como não confiável.

## Roadmap

| # | Milestone | Âmbito |
|---|---|---|
| 01 | Product Discovery | PRD, C4, domínios, ADRs, identidade visual |
| 02 | Core Foundation | Monorepo, Docker, Laravel, React, MySQL, autenticação (passkey + TOTP), contratos, CI |
| 03 | KAI Intelligence | AI Engine, LLM Gateway, conversa em streaming, RabbitMQ + Outbox, OpenTelemetry |
| 04 | Memory System | Qdrant, embeddings, RAG com fontes, memória controlável |
| 05 | Agent Framework | Agent e Tool Registry, missões, aprovações, avaliações |
| 06 | Voice Experience | STT, TTS, interrupção |
| 07 | Integrations & Automation | GitHub, Docker, webhooks, workflows |
| 08 | Advanced Intelligence | Vision, analytics, developer e system intelligence |
| 09 | Distributed Architecture | Extracção de serviços com justificação |
| 10 | Production Readiness | CD, segurança, carga, backups, deploy |

O MVP é uma fatia vertical fina: login, chat em streaming, uma ferramenta só de leitura, uma escrita com aprovação humana, auditoria e um trace de ponta a ponta. Ver [`analysis.md` §6](docs/product/analysis.md#6-mvp-fatia-vertical-fina).

## Quick start

Em construção (M02). Hoje já é possível:

```bash
docker compose up -d --wait
docker compose exec api php artisan migrate
docker compose exec api php artisan kai:create-owner "Nome" owner@example.test
docker compose exec api php artisan kai:enable-totp owner@example.test
```

O `kai:enable-totp` mostra **uma única vez** o URI `otpauth://` (para a app autenticadora) e os códigos de recuperação. Depois, em `http://localhost:5173`, entra com o código TOTP e usa "Registar passkey" para passares a entrar com a passkey. Gerir credenciais exige um login nos últimos 10 minutos.

Se suspeitares de que a conta foi comprometida: `kai:enable-totp <email> --force` roda o segredo e revoga todas as sessões; junta `--revoke-passkeys` para apagar também as passkeys.

RabbitMQ e observabilidade (`otel-lgtm`, Grafana em `http://127.0.0.1:3000`) são opcionais até haver consumidores e ficam nos *profiles* `messaging` e `observability`. Recusam arrancar sem passwords fortes: gera-as com `scripts/dev/passwords.sh`, redireccionando o output para o ficheiro de ambiente ([`rabbitmq.md`](docs/engineering/rabbitmq.md), [`observability.md`](docs/engineering/observability.md)), e depois:

```bash
docker compose --profile messaging --profile observability up -d --wait
```

E2E de AC-02 (Playwright, numa stack descartável `kai-e2e`; pára primeiro a stack de dev com `docker compose stop`):

```bash
scripts/e2e.sh
```

## Contribuir e segurança

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`SECURITY.md`](SECURITY.md)

## Licença

Licença decidida: **Apache-2.0** (D-02). O ficheiro `LICENSE` será acrescentado antes da primeira publicação de código. Até lá, aplicam-se os direitos de autor por omissão.
