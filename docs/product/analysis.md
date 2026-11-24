# KAI — Análise de arquitecto (Fase 1)

- **Estado:** aprovada pelo owner a 2026-11-20
- **Fonte:** `docs/product/1_KAI_Product_Vision_Architecture_Roadmap.pdf` (V1.0, 21 páginas)
- **Método:**
  - 4 perspectivas independentes em modo só-leitura (produto, segurança/privacidade, AI engineering, plataforma/DevOps), sintetizadas aqui.
  - Divergências entre elas na secção 9.
  - Factos externos verificados em fontes oficiais a 2026-11-20 (secção 1).

**Etiquetas:**
- **[C]** confirmado: está no PDF (p.N) ou é decisão do owner (D-xx).
- **[H]** hipótese, com justificação.
- **[P]** decisão pendente.

---

## 0. Decisões do owner (passam a [C])

| ID | Decisão | Nota |
|---|---|---|
| D-01 | Todos os artefactos do repositório em PT-PT, incluindo o README | Sobrepõe-se ao "README em inglês" da p.19 (ADR-0012). Identificadores de código e tipos Conventional Commits (`feat:`, `fix:`) ficam em inglês. |
| D-02 | Licença Apache-2.0 | Registada; o ficheiro `LICENSE` ainda não foi criado |
| D-03 | Deploy: local (Docker Compose) agora, VPS única depois | Sem Kubernetes (p.17) |
| D-04 | O Claude Code corre dentro do WSL | — |
| D-05 | Autenticação do owner: passkey (WebAuthn) + TOTP, com códigos de recuperação; re-autenticação no nível 5; conta criada por CLI | Suporte a passkeys no Laravel 13 confirmado de 1.ª parte via `laravel/fortify` (P-017, fechada) |
| D-06 | Autenticação entre serviços: JWS assimétrico de curta duração + rede Docker privada; um utilizador RabbitMQ por serviço; mTLS só com vários hosts | Responde à p.20 |
| D-07 | Indexável na v1: uploads explícitos, conversas (com opt-out) e repositórios do owner, sem ficheiros de segredos | Email e calendário fora da v1. Credenciais e dados sensíveis nunca são indexados. |
| D-08 | LLM do protótipo: Anthropic (cloud) + Ollama (2.º adaptador) + fornecedor falso determinístico para a CI | Responde à p.20 |
| D-09 | Baseline: Laravel 13 · PHP 8.5 · MySQL 8.4 LTS · Python 3.14 · RabbitMQ 4.4 | A versão de patch fixa-se no M02 |
| D-10 | MVP: leitura livre + escrita interna sujeita a aprovação | Coerente com o nível 1 da p.13 |
| D-11 | Roadmap: antecipar o mínimo | CI no M02. RabbitMQ, Outbox/DLQ mínimos e tracing (`grafana/otel-lgtm`) no M03. CD, SBOM e a stack de observabilidade completa no M10. |
| D-12 | Object storage: SeaweedFS, acedido só pela API S3 (Cloudflare R2 como opção cloud); entra no M04 | Substitui o MinIO, que foi arquivado |
| D-13 | Cache e sessões: Redis 8 | Fiel ao PDF |
| D-14 | Limites de custo e de execução a definir no M03, depois de medir com o conjunto de avaliação | Continua [P] (P-002) |
| D-15 | A Fase 2 do harness corre numa sessão Claude Code dentro do WSL | — |
| D-16 | As 5 passagens reconstruídas do PDF estão confirmadas | Visão (p.4), ficha (p.2), "Orchestrator Agent" (p.9), sequência inicial (p.20), regra de trabalho (p.21) |
| D-17 | O `CLAUDE.md` refere `docs/product/kai-vision.md` sem o importar | Poupa cerca de 470 linhas de contexto por sessão; o ficheiro é lido quando a tarefa o exigir |
| D-18 | Proposta MCP aprovada: GitHub MCP read-only (PAT fine-grained de um só repositório) no M02; Laravel Boost avaliado no M02, só em local; Playwright mais tarde; Context7 não | Nada instalado; a instalação pede nova aprovação no M02 ([`claude-code-setup.md` §5](../engineering/claude-code-setup.md#5-mcp-proposta-nada-instalado)) |

## 1. Factos externos verificados (2026-11-20)

| Tema | Facto | Fonte |
|---|---|---|
| Laravel | 12: bug fixes até 13 Ago 2026, segurança até 24 Fev 2027. 13: PHP 8.3–8.5, lançado no Q1 2026, bug fixes até Q3 2027, segurança até Q1 2028. | laravel.com/docs/master/releases |
| PHP | 8.3 só recebe correcções de segurança desde 31 Dez 2025. 8.5 tem suporte activo até 31 Dez 2027 e segurança até 31 Dez 2029. 8.6 saiu a 19 Nov 2026. | php.net/supported-versions.php |
| Python | 3.15 em bugfix (3.15.2 de 25 Out 2026); 3.14 em bugfix; 3.10 em fim de vida | devguide.python.org/versions |
| FastAPI | 0.165.0 (18 Nov 2026), requer Python ≥ 3.11 | pypi.org/project/fastapi |
| Laravel Reverb | Documentação oficial; escala horizontalmente com Redis pub/sub | laravel.com/docs/master/reverb |
| Qdrant | v1.20.2 (16 Nov), Apache-2.0 | github.com/qdrant/qdrant |
| Tauri | v2.12.7 (18 Nov); desktop e mobile | github.com/tauri-apps/tauri |
| MySQL | 8.0 em *Sustaining Support* desde 21 Abr 2026; recomendam 8.4 LTS ou 9.7 LTS | mysql.com/support/eol-notice.html |
| MinIO | Repositório arquivado a 25 Abr 2026, já sem manutenção; a edição comunitária é distribuída só como código-fonte | github.com/minio/minio |
| SeaweedFS | Apache-2.0; release 4.54 a 16 Nov 2026 | github.com/seaweedfs/seaweedfs |
| Redis | Redis 8+ sob RSALv2, SSPLv1 ou AGPLv3 | redis.io/legal/licenses |
| RabbitMQ | 4.4.1 (16 Nov 2026), suporte comunitário até 31 Jul 2027 | rabbitmq.com/release-information |
| OWASP LLM Top 10 | genai.owasp.org mostra a edição de 2025; o README do projecto diz "2026, publicado a 4 Ago 2026" | genai.owasp.org; GitHub GenAI-LLM-Top10 |
| LiteLLM | Versões 1.82.7 e 1.82.8 maliciosas publicadas no PyPI a 24 Mar 2026 | InfoQ; JFrog Research |
| Ollama | API compatível com OpenAI, sem `tool_choice` | docs.ollama.com/api/openai-compatibility |

## 2. Visão, limites e não-objectivos

**Visão [C p.4]:** "Criar uma inteligência pessoal que compreenda o contexto do utilizador e execute operações autorizadas, mantendo-o sempre informado e no controlo."
- É um assistente multimodal e extensível, entre o utilizador e o seu ecossistema digital [C p.2, p.4].
- É também um laboratório de engenharia [C p.2].

**Limites [C]:**
- Pessoal primeiro, com a evolução para multi-utilizador preparada (p.2, p.20).
- Web primeiro; desktop (Tauri) numa fase posterior (p.13, p.20); mobile no futuro (p.7).
- Nem tudo entra na v1 (p.2).

**Não-objectivos [C p.5]:**
- Treinar um LLM de raiz.
- Muitos microsserviços antes de haver necessidade.
- Acesso irrestrito do modelo ao SO, às bases de dados ou aos ficheiros.
- Automações sensíveis sem aprovação e auditoria.
- Optimizar para escala massiva antes de validar o produto.
- Implícitos: SaaS na 1.ª fase [C p.20]; Kubernetes sem justificação [C p.17].

## 3. Requisitos

### 3.1 Funcionais

Todos são [C], com a página indicada. A coluna "Fase" é [H].

| ID | Requisito | Origem | Fase |
|---|---|---|---|
| FR-001 | Interacção por texto no Command Center | p.6 | MVP |
| FR-002 | Histórico de conversas | p.6 | MVP |
| FR-003 | Estado dos agentes e das missões activas | p.6 | MVP (1 missão) |
| FR-004–006 | Notificações; actividade recente; indicadores de utilização | p.6 | Depois |
| FR-007 | Núcleo visual animado | p.6 | Depois (no MVP, um badge de estado) |
| FR-008 | Respostas em streaming | p.6 | MVP |
| FR-009 | Contexto conversacional | p.6 | MVP |
| FR-010 | Português e inglês (âmbito em aberto, P-006) | p.6 | MVP (conversa) |
| FR-011 | Pesquisa no histórico | p.6 | Depois |
| FR-012 | Análise de imagens e documentos | p.6 | Depois |
| FR-013 | Respostas com referências e indicação de limitações | p.6 | MVP |
| FR-014–020 | STT, TTS, sessões de voz, detecção de fim de fala, interrupção, activação por botão; wake word mais tarde | p.6, p.20 | M06 |
| FR-021 | Working memory | p.6 | MVP |
| FR-022 | Memória de conversa persistida | p.6 | MVP |
| FR-023 | Memória de longo prazo (episódica, semântica, procedural) | p.6 | M04+ |
| FR-024 | Indexação documental, embeddings, pesquisa semântica, RAG | p.6, p.11 | M04 |
| FR-025 | Consultar, corrigir e eliminar memória persistente | p.5 | M04 |
| FR-026 | Cada memória tem origem, data e política de retenção | p.11 | M04 |
| FR-027 | Permissões aplicadas também na recuperação | p.11 | M04 |
| FR-028 | Agent Registry: identidade, instruções, modelo, ferramentas, permissões, limites, versões | p.6, p.10 | M05 |
| FR-029 | Métricas e avaliação de agentes | p.6 | M05 |
| FR-030 | 9 agentes iniciais (Orchestrator, Research, Developer, DevOps, Data Analyst, Document, Productivity, Security, Vision) | p.9–10 | MVP: 1 agente implícito |
| FR-031 | Catálogo de conectores (GitHub, GitLab, Docker, calendário, email, BD, APIs, webhooks, MCP) | p.6 | MVP: 1 conector (GitHub, só leitura) |
| FR-032 | Tool Registry: nome, versão, JSON Schema de entrada e saída, permissões, modo, timeout e retry, aprovação, auditoria, disponibilidade | p.10 | MVP (subconjunto) |
| FR-033–036 | Workflows: triggers, condições, acções, agendamento, webhooks, execução assíncrona com retry e histórico, editor visual | p.6 | M07 (editor visual em aberto, P-010) |
| FR-037–039 | Developer Intelligence | p.6 | M08 |
| FR-040 | System Intelligence | p.6 | M08 |
| FR-041–042 | Data Intelligence | p.6 | M08 |
| FR-043 | Vision e multimodal | p.6 | M08 |
| FR-044 | Autenticação por passkey + TOTP (D-05) | p.6, p.14 | MVP |
| FR-045 | MFA e gestão de sessões (listar e revogar) | p.6, p.14 | MVP |
| FR-046 | RBAC e permissões por recurso, agente e ferramenta | p.6, p.14 | MVP: só por ferramenta |
| FR-047 | Aprovações | p.6, p.13 | MVP |
| FR-048 | Auditoria | p.6, p.14 | MVP |
| FR-049 | Segredos fora do código e das mensagens | p.14 | MVP |
| FR-050 | Rate limiting, quotas e limites de custo | p.14 | MVP (valores definidos no M03) |
| FR-051 | Isolamento de utilizadores (`user_id` em todas as linhas próprias) | p.6, p.11 | MVP |
| FR-052 | Retenção, exportação e eliminação de dados | p.14 | M04+ |
| FR-053 | Ciclo de execução de 9 etapas | p.9 | MVP (subconjunto, secção 5.2) |
| FR-054 | Tarefas de uma etapa e missões multi-etapa | p.9 | MVP: uma etapa + aprovação |
| FR-055 | Execução observável, cancelável, limitada e recuperável | p.9 | MVP: observável, limitada e cancelável |
| FR-056 | Validação de permissões fora do LLM | p.9 | MVP |
| FR-057 | Validar entradas e saídas das ferramentas | p.9, p.14 | MVP |
| FR-058 | Guardar eventos e resultados relevantes | p.9 | MVP |
| FR-059 | Workflows explícitos para tarefas previsíveis; agentes para tarefas que exigem interpretação | p.9 | M05/M07 |
| FR-060 | Entidade Mission | p.10 | MVP (subconjunto) |
| FR-061 | 8 estados da missão | p.10 | MVP sem PLANNING nem PAUSED |
| FR-062 | Níveis de operação 1–6 | p.13 | MVP: níveis 1, 4 e 6; recusa por omissão |
| FR-063 | Conteúdo externo é não confiável | p.14 | MVP |
| FR-064 | Pipeline RAG com reranking opcional e respostas com fontes | p.11 | M04 |
| FR-065 | Indexação assíncrona e idempotente | p.11 | M04 |
| FR-066 | UI dark-first, minimalista e acessível | p.12 | MVP |
| FR-067 | 12 áreas de navegação | p.12 | MVP: Conversations, Missions/Approvals, Security & Audit |
| FR-068 | 7 estados visuais do núcleo | p.12 | MVP sem Listening nem Speaking |

### 3.2 Não funcionais

O PDF não fixa metas numéricas (A-15). As metas [H] confirmam-se no M01.

| ID | Requisito | Meta | Etiqueta |
|---|---|---|---|
| NFR-001 | Todas as execuções de ferramentas passam por um Policy Enforcement Point. Um teste de arquitectura prova que nenhum caminho chega a um adaptador sem *grant*. | 100% | [C p.9, p.13] / teste [H] |
| NFR-002 | Execuções, aprovações, recusas e logins geram auditoria append-only: actor, agente@versão, ferramenta@versão, modo, nível, hash dos argumentos, decisão, trace_id. | 100% | [C p.6, p.14] / campos [H] |
| NFR-003 | Operações de nível 6 são sempre recusadas, provado por uma suite negativa versionada. | 100% | [C p.13] |
| NFR-004 | Uma aprovação está ligada ao hash exacto dos argumentos, é de uso único e expira. | ≤ 15 min | [H] |
| NFR-005 | Conteúdo externo não altera a allowlist, o nível nem as instruções. Uma suite de prompt injection na CI bloqueia o merge se houver uma acção de nível ≥ 4 não aprovada. | 0 falhas | [C p.14, p.19] / gate [H] |
| NFR-006 | Inputs e outputs das ferramentas são validados por JSON Schema. Os inválidos são rejeitados, nunca reparados em silêncio. | 100% | [C p.9, p.10] |
| NFR-007 | Nenhum segredo em código, mensagens, prompts, logs ou commits; secret scanning na CI. | 0 | [C p.14, p.19, p.21] |
| NFR-008 | Encriptação em trânsito (TLS em todo o tráfego que sai do host) e em repouso. | — | [C p.14] |
| NFR-009 | Isolamento por `user_id` aplicado no servidor (MySQL, Qdrant, storage); os testes provam zero resultados cruzados. | 0 | [C p.11] |
| NFR-010 | A eliminação de memória propaga-se a todos os stores. | ≤ 24 h nos primários; ≤ 30 d nos backups | [C p.5, p.11] / prazos [H] |
| NFR-011 | Limites duros por missão (tokens, custo, passos, chamadas de ferramenta, tempo), tecto diário e kill switch. | Valores no M03 | [C p.9, p.14, p.20] |
| NFR-012 | Cada ferramenta tem timeout, retry limitado e isolamento. | — | [C p.10, p.14] |
| NFR-013 | Logs e traces levam IDs, sem conteúdo nem dados sensíveis. | 100% | [C p.21] / [H] |
| NFR-014 | Ferramentas de fetch com egress controlado: bloqueiam IPs privados, loopback, link-local e metadata, após resolução DNS e em cada redirect. | — | [H] |
| NFR-015 | Tempo até ao 1.º token (chat com modelo cloud), medido no cliente. | p50 ≤ 1,5 s · p95 ≤ 3 s | [H] |
| NFR-016 | Latência por tipo de tarefa. | Q&A p95 ≤ 8 s · RAG p95 ≤ 12 s · 1.º evento de missão ≤ 3 s | [C p.19] / metas [H] |
| NFR-017 | Todas as chamadas ao LLM registam modelo, versão do prompt, tokens, custo, latência e trace_id. | 100% | [C p.11, p.14] |
| NFR-018 | Groundedness; todas as respostas baseadas em documentos citam a fonte. | ≥ 0,90 · 100% | [C p.19] / metas [H] |
| NFR-019 | Retrieval Quality. | recall@5 ≥ 0,85 | [C p.19] / [H] |
| NFR-020 | Task Success; uma regressão acima de 3 pp bloqueia a release. | ≥ 80% | [C p.19] / [H] |
| NFR-021 | Tool Success, sem contar recusas de política. | ≥ 95% | [C p.19] / [H] |
| NFR-022 | Frescura da indexação (PDF de 20 páginas pesquisável). | p95 ≤ 60 s | [H] |
| NFR-023 | Disponibilidade em produção numa VPS única. | 99%/mês | [C p.19] / [H] |
| NFR-024 | Backups com teste de restore no fim de cada milestone. | RPO ≤ 24 h · RTO ≤ 4 h | [C p.17] / [H] |
| NFR-025 | Deploy com um comando; migrations expand/contract; rollback. | ≤ 15 min | [C p.17] / [H] |
| NFR-026 | Observabilidade: spans em todos os pedidos HTTP e handlers AMQP; `traceparent` em todas as mensagens; logs estruturados com trace_id. | 100% | [C p.5, p.14] / [H] |
| NFR-027 | Health checks (liveness e readiness) e graceful shutdown. | ≤ 30 s | [C p.15] |
| NFR-028 | Nenhuma mensagem se perde com o restart do broker; alerta quando a DLQ > 0. | 0 perdas | [C p.15] / [H] |
| NFR-029 | Arranque local, de `docker compose up` até a stack estar funcional. | ≤ 10 min | [H] |
| NFR-030 | Acessibilidade da UI. | WCAG 2.2 AA | [C p.12] / nível [H] |

## 4. Ambiguidades, decisões pendentes e riscos

### 4.1 Ambiguidades do PDF

| ID | Ambiguidade | Estado |
|---|---|---|
| A-01 | "KAI" é marca, ecossistema e nome da inteligência ao mesmo tempo | Confirmado (D-16) |
| A-02 | "KAI Core" (p.4, p.9) vs "Core Platform" (p.7): quem planeia e orquestra? | Proposta na secção 5 (ADR-0002) |
| A-03 | O Tool Registry está no Core (Laravel), mas o "Tool Execution" é candidato a serviço Python | Registo e política no Laravel, execução no Python (secção 5) |
| A-04 | Onde vive a validação de permissões | PDP no Laravel, PEP nos dois lados (ADR-0004) |
| A-05 | O diagrama mostra 5 estados da missão e a tabela 8, sem transições definidas | Proposta 5.3 (P-003) |
| A-06 | Correspondência entre modos de ferramenta e níveis 1–6 | Proposta 5.4 (P-004) |
| A-07 | Caminho do streaming de tokens | Reverb, sujeito a spike (ADR-0009) |
| A-08 | O RabbitMQ só aparece no M07 e o Outbox/DLQ no M09 | Antecipados para o M03 (D-11) |
| A-09 | "Instrumentar desde o início" vs observabilidade e CI/CD só no M10 | CI no M02, tracing no M03 (D-11) |
| A-10 | A stack da ficha (p.2) omite Qdrant e MinIO; Tauri listado como cliente | Resolvido por D-09, D-12, D-13 |
| A-11 | Redis também usado como fila? | Proposta [H]: Redis só para cache, sessões, rate limiting e Reverb; filas entre serviços só no RabbitMQ |
| A-12 | Caixas MESSAGING e PERSISTENCE vazias no diagrama da p.7; falta a Observability | **Resolvido (2026-11-20)**, confirmado visualmente: as caixas não estavam vazias (MESSAGING = RabbitMQ+Redis; PERSISTENCE = MySQL+Qdrant+MinIO), só o texto extraído do PDF as tinha perdido. A Observability aparece como coluna à parte, ligada por linha tracejada à fronteira Core Platform/AI Intelligence. Ver `kai-vision.md` §05 |
| A-13 | `integration_credentials` em MySQL vs "segredos fora do código e das mensagens" | Proposta: envelope encryption (P-007) |
| A-14 | Uso pessoal vs MFA, RBAC e isolamento | `user_id` em tudo desde o dia 1, uso single-user [H] |
| A-15 | Nenhum NFR numérico | Metas [H] na secção 3.2 |
| A-16 | O Daily Briefing precisa de email e calendário, que nenhum milestone prevê | P-008 |
| A-17 | 9 agentes, 12 módulos e 12 áreas, sem prioridades | MVP na secção 6 |
| A-18 | Editor visual de workflows sem fase | P-010 |
| A-19 | Âmbito do PT/EN | P-006 |
| A-20 | "Cloud para produção" sem dizer qual | Resolvido por D-03 |
| A-21 | Fornecedor de LLM do protótipo | Resolvido por D-08 |
| A-22 | Várias secções em colunas cuja atribuição ao título é inferida (caps. 6, 8, 10, 11, 12, 13, 15) | Confirmar visualmente |
| A-23 | O prompt da p.21 refere `kai_Product_...pdf`, mas o ficheiro é `1_KAI_...pdf` | P-001 |
| A-24 | Documento V1.0 com estado "proposta inicial"; sem política de versões | Registado |
| A-25 | A hipótese de MVP "ferramenta só-leitura + aprovação" contradizia o nível 1 da p.13 | Resolvido por D-10 |
| A-26 | Edição do OWASP LLM Top 10 diverge entre páginas oficiais (2025 vs 2026) | A 2026 existe (Ago 2026), mas a lista não foi verificada; usar os IDs 2025, verificados a 2026-11-20, até a verificar [P] |

### 4.2 Decisões pendentes

A recomendação vem primeiro em cada linha.

| ID | Decisão | Recomendação | Quando |
|---|---|---|---|
| P-001 | Nome do ficheiro PDF | Manter `1_KAI_...pdf` e corrigir as referências | Harness |
| P-002 | Valores dos limites de custo e de passos | Medir com o conjunto de avaliação (D-14); ponto de partida: $1 por missão e $5 por dia | M03 |
| P-003 | Transições da missão | **Fechado** → [ADR-0013](../adr/0013-modelo-de-seguranca.md) | M01 |
| P-004 | Tabela nível ↔ modo ↔ aprovação, incluindo a regra de *taint* | **Fechado** → [ADR-0013](../adr/0013-modelo-de-seguranca.md) | M01 |
| P-005 | Lista do nível 6 | **Fechado** → [ADR-0013](../adr/0013-modelo-de-seguranca.md): shell/SQL irrestrito, ler segredos, desligar auditoria, alterar as próprias permissões | M01 |
| P-006 | PT/EN só na conversa ou também na UI | **Fechado** → [`prd.md` §3](prd.md#3-âmbito-do-mvp-fatia-vertical-fina): conversa em PT/EN; UI em PT primeiro, com i18n preparado | M01 |
| P-007 | Cifra de `integration_credentials` | Envelope encryption (AES-256-GCM, chave mestra separada da `APP_KEY`, rotação); libertação ao Python ligada a um *grant* | M07 |
| P-008 | Daily Briefing (email e calendário) | **Fechado** → [`prd.md` §3](prd.md#3-âmbito-do-mvp-fatia-vertical-fina): fora da v1; o 1.º cenário de demo é o Developer Assistant | M01 |
| P-009 | Modelo de embeddings | Multilingue; spike PT/EN local vs cloud | M04 |
| P-010 | Editor visual de workflows | Fora de âmbito; primeiro workflows por definição | M07 |
| P-011 | Estratégia e custo de STT/TTS (p.20) | Spike | M06 |
| P-012 | Ferramentas locais vs cloud (p.20) | Decidir com o desktop | Pós-M10 |
| P-013 | Exposição da produção | Só por VPN ou túnel até ao M10 | M10 |
| P-014 | Quem é dono de `document_chunks` (secção 9) | Schema próprio do AI Engine | M04 |
| P-015 | Demo pública (custo e chaves) | **Fechado** → [`.env.example`](../../.env.example): `MODEL_PROVIDER=fake` por omissão para quem clona o repositório | M02 |
| P-016 | Modelo-juiz das avaliações e orçamento mensal | Modelo fixado, calibrado com cerca de 50 itens etiquetados por humanos | M05 |
| P-017 | Passkeys no Laravel 13 (1.ª parte ou pacote) | **Fechado** (2026-11-20): suporte de 1.ª parte confirmado — `laravel/fortify` v1.43.0 + `laravel/passkeys` v0.3.0 (MIT, PHP ^8.2, Laravel ^12\|^13), instalado em `apps/api`. Cobre também o TOTP de D-05 (`pragmarx/google2fa`) | M02 |
| P-018 | Um turno de conversa é uma missão de um passo no M03? | **Fechado** (2026-11-23, [SPEC-004](../specs/004-ai-engine-m03.md)): sim, o Laravel envia sempre `mission_id`. A AC-09 fala de missões e o `ai.mission.cancel.requested.v1` exige `mission_id`; o M05 generaliza | M03 (E4.1) |
| P-019 | Bibliotecas AMQP e OpenTelemetry (PHP e Python) | **Fechado** (2026-11-23) → [ADR-0016](../adr/0016-clientes-amqp-php-e-python.md) (`php-amqplib` 3.7.5, LGPL aceite pelo owner; `aio-pika` 10.2.3) e [ADR-0017](../adr/0017-sdks-opentelemetry-e-semconv.md) (instrumentação manual, semconv 1.44.0) | M03 (E1.2, E1.3) |
| P-020 | Onde guarda o AI Engine a inbox de deduplicação? | **Fechado** (2026-11-23): Redis (`SET NX`, TTL de 7 dias, só IDs), com utilizador ACL próprio e `redis-py` como dependência nova ([SPEC-004](../specs/004-ai-engine-m03.md) §10). **Revisto pelo owner a 2026-11-23 (E3.4a):** um Redis **próprio** do ai-engine (`ai-engine-redis`, rede interna `ai-engine-data`), não o do Laravel, que não tem autenticação e está na rede `default`, de onde a E3.2 tirou o ai-engine | M03 (E3.4) |
| P-021 | Dependências do `apps/ai-engine` | **Primeira lista aprovada** (2026-11-23, E3.2): imagem `python:3.14.9-slim-trixie` por digest, `fastapi` 0.162.2, `uvicorn` 0.54.0, `aio-pika` 10.2.3; dev: `pytest` 9.2.0, `httpx` 0.28.1, `jsonschema` 4.26.0, `ruff` 0.17.4, `mypy` 2.4.1; `uv` 0.13.7 só para os locks ([`apps/ai-engine/README.md`](../../apps/ai-engine/README.md)). **Segunda lista aprovada** (2026-11-23, E3.3): `anthropic` 2.6.0 (Apache-2.0) com as transitivas `httpx2`/`httpcore2` 2.16.0 (BSD-3), `jiter` 0.19.0, `docstring-parser` 0.18.0, `sniffio` 1.3.1 e `truststore` 0.10.5; o adaptador Ollama usa o `httpx2` do SDK (uma só biblioteca HTTP no runtime), não o `httpx`, que fica só em dev. **Terceira lista aprovada** (2026-11-23, E3.4a): `redis` 8.1.0 (MIT) e `jsonschema` 4.26.0 em runtime (já aprovado em dev); o `pytest-asyncio` deixou de ser preciso. Seguinte: E7.1 (OpenTelemetry) | M03 |
| P-022 | `prompt_version` no `ai.model.usage.recorded.v1` (NFR-017)? | Só no span no M03; campo opcional (compatível) se a auditoria de custos o pedir | M03 |
| P-023 | `axe-core` como dependência de dev da web (testes de acessibilidade)? | **Fechado** (2026-11-24, owner): sim, só em dev, 4.14.0, MPL-2.0 ([SPEC-005](../specs/005-prototipo-chat.md)) | M03 |
| P-024 | Como se escolhe o cenário do chat simulado? | **Fechado** (2026-11-24, owner): selector no aviso "Respostas simuladas" ([SPEC-005](../specs/005-prototipo-chat.md)) | M03 |
| P-025 | Janela de contexto de cada turno no M03 | **Fechado** (2026-11-24, owner): últimas 20 mensagens concluídas, até 48 000 caracteres ([SPEC-006](../specs/006-conversas-e-envio-de-turnos.md)); revista na E6.3 | M03 |
| P-026 | Limites provisórios por turno (P-002) | **Fechado** (2026-11-24, owner): 1024 tokens de saída, 60 s, 0,25 USD; 10 envios por minuto ([SPEC-006](../specs/006-conversas-e-envio-de-turnos.md)); medidos na E6.3 | M03 |
| P-027 | Contrato da API da SPA | **Fechado** (2026-11-24, owner): OpenAPI `public-v1.yaml` antes do código; tipos gerados no E5.1 ([SPEC-006](../specs/006-conversas-e-envio-de-turnos.md)) | M03 |
| P-028 | Margem do vigia de turnos órfãos e janela do canal depois do fim | 120 s depois do timeout; canal autorizado até 10 min depois do fim ([SPEC-007](../specs/007-eventos-de-turno-e-canal.md)) | M03 |

### 4.3 Riscos

P = probabilidade, I = impacto (A alto, M médio, B baixo).

| Risco | P/I | Mitigação |
|---|---|---|
| Prompt injection indirecta (documentos, repositórios, web) | A/A | Origem marcada no conteúdo; uma missão que leu conteúdo externo fica "tainted" e o nível 4 passa a exigir aprovação; política determinística fora do LLM; suite de injection na CI |
| Exfiltração por ferramentas (imagens markdown, links, query strings) | A/A | CSP `img-src 'self'`; imagens remotas nunca carregadas automaticamente; envio para fora depois de ler dados privados exige aprovação; egress controlado |
| Excesso de autonomia / abuso de ferramentas | A/A | Ferramentas estreitas e tipadas; *grants* de uso único assinados pelo Laravel; credenciais só de leitura por omissão |
| Argumentos alucinados | A/M | Schema estrito (`additionalProperties: false`); validação de IDs e do dono; o pedido de aprovação mostra os argumentos reais |
| Alucinação nas respostas | A/M | Citações obrigatórias; avaliação de groundedness; limitações explícitas |
| Custo descontrolado | M/A | Tectos duros, estimativa antes da chamada, detecção de loops, kill switch |
| Memória ou RAG envenenados | M/A | Memória de longo prazo só com confirmação do owner; quarentena do que vem de fontes não confiáveis |
| Fuga de dados entre utilizadores na pesquisa vectorial | B na v1 / A depois | Filtro `user_id` imposto pelo código de consulta, nunca pelo LLM; re-verificação no MySQL |
| Segredos enviados ao fornecedor de LLM | M/A | Credenciais nunca entram no contexto; outputs das ferramentas passam por scan de segredos |
| Supply chain | M/A | Lockfiles com hash, SBOM, digests fixados; porta própria para o LLM (ADR-0006) |
| Scope creep | A/A | MVP congelado por critérios de aceitação |
| Infraestrutura antes de valor | A/A | Cada serviço só entra quando um critério de aceitação o exige (p.16) |
| Projecto de uma pessoa que estagna | M/A | Fatias pequenas e demonstráveis |
| Revisores sem chaves de API | M/M | Fornecedor fake por omissão |
| Convenções OTel de mensageria ainda instáveis | M/B | Fixar a versão das semconv |
| Object storage que muda de novo | M/M | Só API S3, com teste de contrato S3 |
| Repositório em PT reduz o alcance internacional | M/M | Decisão do owner (D-01), reversível (ADR-0012) |

## 5. Bounded contexts, responsabilidades e contratos

### 5.1 Princípio [H]

**Laravel:**
- Sistema de registo e Policy Decision Point.
- Dono das máquinas de estado, das aprovações e da auditoria.
- Único escritor de missões, auditoria e memórias.

**Python:** runtime cognitivo e de execução de ferramentas, sem estado de negócio autoritativo.

"KAI Core" (p.4, p.9) designa o ciclo lógico que atravessa os dois.

| Contexto | Entidades (p.11) | Dono | Fonte de verdade | Invariantes |
|---|---|---|---|---|
| Identity & Access | users, user_preferences, sessions | Laravel | MySQL | Passkey + TOTP; `user_id` em todas as linhas próprias |
| Conversations | conversations, messages, attachments | Laravel | MySQL; binários no storage (M04) | Mensagens append-only; cada resposta é finalizada uma só vez |
| Agents | agents, agent_versions, agent_tools, agent_permissions | Laravel configura; Python executa | MySQL | Cada execução fixa uma `agent_version` imutável |
| Tool Registry & Policy | tools, tool_versions | Laravel | MySQL | Schemas, modo, nível fixo, timeout, aprovação; o nível nunca é escolhido pelo LLM |
| Tool Execution | tool_executions | Python executa; Laravel regista | MySQL | Só corre com *grant* válido; idempotente por passo |
| Missions | missions, mission_steps, mission_events | Laravel | MySQL | Só o Laravel muda o estado |
| Approvals | mission_approvals | Laravel | MySQL | Só um humano decide; ligada ao hash dos argumentos |
| Audit | audit_logs | Laravel | MySQL (append-only) | Cumpre o NFR-002 |
| Knowledge & Memory | memories, knowledge_sources, knowledge_documents, document_chunks | Laravel (metadados e memórias); Python (pipeline e Qdrant) | MySQL; o Qdrant é derivado | Indexação idempotente; ACL aplicada na recuperação; dono dos chunks em aberto (P-014) |
| Integrations | integrations, integration_credentials, webhooks | Laravel | MySQL, cifrado (P-007) | Segredos nunca em mensagens nem em prompts |
| Workflows | workflows, workflow_versions, workflow_executions | Laravel | MySQL | Retry e histórico |
| Notifications | notifications | Laravel | MySQL | — |
| Model Providers & Usage | model_providers, model_usage | Laravel configura; Python executa (LLM Gateway) | MySQL | O Laravel define o orçamento; o Python aplica-o em cada chamada |
| AI Orchestration | — | Python | Sem estado | Planeamento separado da execução (p.9) |

**Validação de permissões [H]:**
- **PDP no Laravel.**
- **PEP-1, no gateway Laravel:** verifica a identidade, a sessão e o dono do recurso.
- **PEP-2, no Tool Execution (Python):** verifica offline um *execution grant*. É um JWS assinado pelo Laravel, válido no máximo 60 s e de uso único. Fica ligado a missão, passo, ferramenta@versão, hash dos argumentos, modo, nível e dono. O Python só tem a chave pública.
- Filtrar a lista de ferramentas mostrada ao LLM reduz a superfície, mas não é enforcement.

### 5.2 Ciclo de 9 etapas [H]

| # | Etapa | Dono | Usa LLM? |
|---|---|---|---|
| 1 | Input | Laravel | Não. Autentica, persiste e cria a missão em `PENDING`. |
| 2 | Context Builder | Python | Não. Janela de conversa, pesquisa filtrada e snapshot de permissões vindo do Laravel. |
| 3 | Intent & Planning | Python (LLM); o Laravel persiste | Sim. Plano estruturado, validado por schema. |
| 4 | Agent Selection | Python | Não na v1 (regras fixas) |
| 5 | Tool Selection | O LLM propõe, o Python valida o schema, o Laravel decide | Sim, só para propor |
| 6 | Execution | Python, com *grant* | Não |
| 7 | Result Evaluation | Python | Não em runtime (o juiz LLM só corre nas avaliações) |
| 8 | Response Generation | Python, em streaming | Sim |
| 9 | Memory Update | O Python propõe; o Laravel decide pela política (na v1, o owner confirma) | Sim, só para extrair |

### 5.3 Máquina de estados da missão (proposta, P-003)

Transições:
- `PENDING → PLANNING → RUNNING`
- `RUNNING ⇄ AWAITING_APPROVAL`
- `RUNNING ⇄ PAUSED`
- `RUNNING → COMPLETED | FAILED`
- De qualquer estado não terminal `→ CANCELLED`
- Aprovação rejeitada `→ CANCELLED`
- Aprovação expirada `→ FAILED`, com motivo `approval_timeout`

Grafia canónica: `AWAITING_APPROVAL`.

### 5.4 Níveis, modos e aprovação (proposta, P-004)

| Nível (p.13) | Modo (p.10) | Aprovação |
|---|---|---|
| 1 Consulta | read-only | Nenhuma; só verificação de acesso |
| 2 Análise | read-only | Nenhuma, dentro do âmbito autorizado |
| 3 Rascunho | draft | Nenhuma; nunca envia nem publica |
| 4 Alteração | write | Depende da política. Uma alteração interna e reversível pode ser automática. Uma alteração externa, irreversível ou numa missão *tainted* exige aprovação. |
| 5 Sensível | write | Aprovação explícita sempre, re-autenticação nos últimos 10 min e auditoria |
| 6 Proibida | — | Nunca registada nem exposta ao LLM; sempre recusada |

### 5.5 Contratos Laravel ↔ Python [H]

**Síncronos (OpenAPI 3.1, rede privada, JWS conforme D-06):**
- Python → Laravel `POST /internal/v1/tool-authorizations`. Responde `allow` com *grant*, `deny` ou `requires_approval`.
- Laravel → Python `/health/live` e `/health/ready`.
- Laravel → Python `POST /v1/retrieval/search` (a partir do M04).

**Assíncronos (RabbitMQ 4.4):**
- Definição: AsyncAPI 3.x + JSON Schema.
- Exchanges `kai.commands` e `kai.events`; quorum queues; DLX com retry, backoff e jitter.

Mensagens:
1. `ai.conversation.turn.requested.v1`
2. `ai.conversation.turn.completed.v1` / `ai.conversation.turn.failed.v1`
3. `ai.mission.step.reported.v1`
4. `ai.mission.step.resume.v1`
5. `ai.mission.cancel.requested.v1`
6. `ai.model.usage.recorded.v1`
7. A partir do M04: `knowledge.document.index.requested.v1` / `knowledge.document.indexed.v1` / `knowledge.document.failed.v1`

**Envelope:** `id` (UUIDv7), `type` com a major no nome, `occurred_at`, `correlation_id`, `causation_id`, `idempotency_key`, `producer`, `traceparent`.

**Versionamento:**
- Alterações aditivas mantêm a major.
- Alterações incompatíveis criam uma major nova, publicada em paralelo durante pelo menos um milestone.
- Os contratos vivem em `packages/contracts`, validados na CI pelos dois lados.
- Os payloads serializados dos jobs Laravel nunca atravessam linguagens.

**Outbox e inbox:**
- Outbox sempre no Laravel, na mesma transacção que a alteração de estado.
- Outbox no Python só onde ele tenha estado próprio (P-014).
- Todos os consumidores têm uma inbox para deduplicar.

**Streaming de tokens:**
- O Python publica deltas agregados (cerca de 50 ms, com `seq`) num canal privado do Reverb, `run.{id}`, autorizado pelo Laravel.
- A mensagem final chega pela mensagem 2, e o cliente reconcilia com ela.
- Os deltas não passam pelo RabbitMQ.
- Se o spike mostrar que não funciona, o fallback é SSE através do Laravel.

**Trace:**
- O `traceparent` é guardado na linha do outbox, passa para o header AMQP e dá origem a um span CONSUMER no Python, filho do span de origem.
- Versão das semconv fixada, porque ainda estão em estado *Development*.

## 6. MVP: fatia vertical fina

**Âmbito:**
- React: login (passkey + TOTP), chat em streaming, aprovação, vista de auditoria.
- Laravel: Identity, Conversations, Missions, Approvals, Audit, Tool Registry e Policy, Outbox.
- RabbitMQ.
- Python: LLM Gateway (Anthropic, Ollama, fake), Context Builder, Tool Execution com *grants*.
- Infraestrutura: Reverb + Redis, MySQL 8.4, `grafana/otel-lgtm`.

**Ferramentas:**
- `github.repo.read`: nível 1, read-only, sobre um repositório público configurado.
- `notes.save`: nível 4, write, interna e reversível, com aprovação obrigatória.

**Fora do MVP:** Qdrant, object storage, voz, núcleo 3D, UI do Agent Registry, RBAC completo, registo público.

**Critérios de aceitação:**
- **AC-01:** Dado um clone limpo com `.env.example` copiado, quando corro `docker compose up`, então todos os serviços ficam *healthy* em ≤ 10 min e nenhum segredo está no repositório.
- **AC-02:** Dado o owner criado por CLI, quando faz login com passkey (ou TOTP), então obtém uma sessão, e uma sessão revogada deixa de funcionar.
- **AC-03:** Dado o owner autenticado, quando envia uma mensagem, então os tokens aparecem incrementalmente e a mensagem e a resposta persistem depois de recarregar a página.
- **AC-04:** Dada uma pergunta sobre o repositório configurado, quando o KAI usa `github.repo.read`, então corre sem pedido de aprovação, o input e o output são validados por schema e a resposta cita o resultado.
- **AC-05:** Dado um pedido para guardar uma nota:
  - quando o KAI propõe `notes.save`, a missão passa a `AWAITING_APPROVAL` e nada é escrito antes da aprovação;
  - se o owner rejeitar, a missão termina em `CANCELLED` sem escrita;
  - se aprovar, a nota é escrita uma única vez.
- **AC-06:** Dada uma ferramenta fora da allowlist ou sem *grant* válido, quando a execução é tentada, então o PEP bloqueia-a, seja qual for o output do LLM.
- **AC-07:** Dado conteúdo de um repositório com "ignore previous instructions…", quando é lido, então não acontece nenhuma chamada de ferramenta extra nem alteração de permissões.
- **AC-08:** Dado qualquer pedido concluído, quando abro a auditoria, então vejo actor, ferramenta, modo, nível, decisão e um trace_id que abre um único trace React → Laravel → RabbitMQ → Python → LLM.
- **AC-09:** Dada uma execução em curso, quando o owner cancela ou o timeout ou orçamento é atingido, então a missão termina em `CANCELLED` ou `FAILED` e a UI mostra o estado Error com o motivo.
- **AC-10:** Dado o fornecedor fake, quando a CI corre, então os testes unitários, de contrato e um E2E passam sem rede nem chaves.

## 7. Plano incremental

São 10 milestones, sem estimativas de duração (p.18).

| M | Objectivo e entregáveis | Critério de aceitação | Depende de |
|---|---|---|---|
| 01 Product Discovery | PRD, casos de uso, FR/NFR confirmados, C4 de nível 1–2, bounded contexts, ADRs 0000–0012 revistos, identidade visual | PRD e ADRs aprovados; P-003, P-004, P-005, P-006 e P-008 fechados | Esta análise |
| 02 Core Foundation | Monorepo mínimo (`apps/api`, `apps/web`, `packages/contracts`), Docker Compose, Laravel 13 + React, MySQL 8.4, login passkey + TOTP, contratos v1, CI (lint, PHPStan, mypy, Pest, Vitest, validação de schemas, secret scan) | AC-01 e AC-02; CI verde | M01 |
| 03 KAI Intelligence | `apps/ai-engine`, LLM Gateway, conversa, streaming (spike do Reverb), contexto, RabbitMQ com Outbox/Inbox/DLQ, OTel + otel-lgtm, limites de custo medidos | AC-03, AC-09 e AC-10; trace ponta-a-ponta | M02 |
| 04 Memory System | Qdrant, embeddings, SeaweedFS (S3), RAG com fontes, memória controlável | PDF respondido com citações; memória visível e apagável; re-indexar não duplica | M03 |
| 05 Agent Framework | Agent e Tool Registry, runtime, missões, aprovações, *grants*, conjunto de avaliação versionado | AC-04 a AC-08; máquina de estados testada; avaliações na CI | M03 (pode correr em paralelo com o M04) |
| 06 Voice Experience | STT, TTS, sessões de voz, interrupção | Conversa por voz mantém o contexto depois de uma interrupção | M03, P-011 |
| 07 Integrations & Automation | GitHub, Docker (sem acesso root ao socket), webhooks, motor de workflows, credenciais cifradas | Workflow com retry e histórico visível | M05 |
| 08 Advanced Intelligence | Vision, analytics, developer e system intelligence | Cenários Developer, Data Analyst e System Diagnosis passam no conjunto de avaliação | M04, M05, M07 |
| 09 Distributed Architecture | Extracções só com ADR que aplique a regra da p.8; Outbox e DLQ endurecidos | Matar um consumidor não perde nem duplica mensagens | M07 |
| 10 Production Readiness | CD, SBOM, scan de imagens, LGTM separado, testes de carga, backups e restore, VPS, segurança; o desktop é avaliado à parte | Deploy em staging, teste de restore, gate de segurança, dashboards | Todos |

## 8. ADRs propostos

"Aceite" quer dizer decidido pelo owner na Fase 1. Os restantes ficam "Proposto" até ao M01.

| ADR | Título | Estado |
|---|---|---|
| 0000 | Registar decisões arquitecturais (MADR) | Aceite |
| 0001 | Modular monolith Laravel + AI Engine Python separado | Aceite |
| 0002 | Fronteira de contratos Laravel ↔ Python | Aceite |
| 0003 | Mensageria RabbitMQ + Outbox/Inbox | Aceite (D-11) |
| 0004 | Modelo de segurança: o LLM não é fronteira; níveis 1–6; PDP no Laravel; *execution grants* | Substituído por ADR-0013 |
| 0005 | Memória e RAG: MySQL, Qdrant e S3 | Aceite |
| 0006 | Abstracção de LLM como porta própria | Aceite (D-08) |
| 0007 | Baseline de versões | Aceite (D-09, D-13) |
| 0008 | Object storage: SeaweedFS via API S3 | Aceite (D-12) |
| 0009 | Streaming de tokens por Reverb | Aceite (condicionado ao spike no M03) |
| 0010 | Autenticação entre serviços: JWS assimétrico + rede privada | Aceite (D-06) |
| 0011 | Desvios ao roadmap do PDF | Aceite (D-11) |
| 0012 | Idioma do repositório: PT-PT | Aceite (D-01) |
| 0013 | Modelo de segurança: o LLM não é fronteira; níveis 1–6 (substitui o ADR-0004) | Aceite |

## 9. Divergências entre perspectivas

1. **RabbitMQ como ponte Laravel ↔ Python.**
   - Produto: a p.7 também admite HTTP síncrono no chat.
   - Plataforma e AI: defendem a fila.
   - Síntese: comandos e eventos passam pelo RabbitMQ, o streaming fica fora dele (D-11).
2. **Quem é dono de `document_chunks`.**
   - AI engineering: o Laravel é o único escritor.
   - Plataforma: o AI Engine deve ter um schema próprio.
   - Síntese: em aberto (P-014); recomendo o schema do AI Engine.
3. **MFA no MVP.** Produto queria cortá-lo; segurança queria mantê-lo. Resolvido por D-05.
4. **Observabilidade inicial.**
   - Produto: OTel + Tempo.
   - Plataforma: `otel-lgtm`.
   - Síntese: `otel-lgtm`.
5. **Redis vs Valkey.** Plataforma recomendou Valkey. Resolvido por D-13 (Redis).
6. **Edição do OWASP LLM Top 10.** As páginas oficiais divergem (A-26).
