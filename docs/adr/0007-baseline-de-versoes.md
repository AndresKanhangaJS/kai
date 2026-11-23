# ADR-0007: Baseline de versões

- **Estado:** Aceite (2026-11-20, D-09, D-13)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.11, p.15–16; ADR-0008

## Contexto
- O PDF propõe "Laravel 12 / PHP 8.3+ como baseline inicial a validar" e "MySQL 8" [C p.15, p.11].
- Diz também que as versões exactas se fixam depois de validar compatibilidade, manutenção e licenciamento [C p.16].
- A validação, feita a 2026-11-20 nas fontes oficiais, mostrou:
  - os bug fixes do Laravel 12 terminaram a 13 Ago 2026;
  - o PHP 8.3 está só com correcções de segurança desde 31 Dez 2025;
  - o MySQL 8.0 passou a *Sustaining Support* a 21 Abr 2026.

## Opções consideradas
1. **Laravel 13 · PHP 8.5 · MySQL 8.4 LTS · Python 3.14 · RabbitMQ 4.4 · Redis 8.** Linhas suportadas e maduras.
2. **As mais recentes: MySQL 9.7 LTS e Python 3.15.** Janela de suporte mais longa, mas mais risco de compatibilidade.
3. **Manter o PDF à letra.** Laravel 12 e MySQL 8.0 já estão fora de suporte normal.

## Decisão
- **Opção 1.** As versões de patch fixam-se no M02, com lockfiles e imagens por tag exacta.

| Componente | Versão | Suporte (fonte oficial) |
|---|---|---|
| Laravel | 13.x | bug fixes até Q3 2027, segurança até Q1 2028 (PHP 8.3–8.5) |
| PHP | 8.5 | activo até 31 Dez 2027, segurança até 31 Dez 2029 |
| MySQL | 8.4 LTS | Oracle Lifetime Support: 5 anos premier + 3 extended |
| Python | 3.14 | bugfix; fim de vida em 2030-10 |
| FastAPI | ≥ 0.165 | requer Python ≥ 3.11 |
| RabbitMQ | 4.4 | suporte comunitário até 31 Jul 2027 |
| Redis | 8.x | RSALv2, SSPLv1 ou AGPLv3 (self-host sem modificação) |
| Qdrant | 1.20.x | Apache-2.0 |

## Consequências
- **Positivas:** tudo em linhas suportadas durante o horizonte do projecto.
- **Negativas:** o RabbitMQ 4.4 tem suporte comunitário curto, por isso é preciso actualizar regularmente. A licença do Redis 8 deve ser revista se o KAI virar SaaS.

## Verificação
- Matriz de versões na CI (M02).
- Revisão desta tabela no início de cada milestone.

## Fontes (verificadas a 2026-11-20)
- laravel.com/docs/master/releases
- php.net/supported-versions.php
- mysql.com/support/eol-notice.html
- devguide.python.org/versions
- pypi.org/project/fastapi
- rabbitmq.com/release-information
- redis.io/legal/licenses
- github.com/qdrant/qdrant
