# KAI — Personal AI Intelligence System

> Versão Markdown de `docs/product/1_KAI_Product_Vision_Architecture_Roadmap.pdf` (V1.0, 21 páginas), transcrita a partir do texto extraído do PDF em 2026-11-20.
>
> - O PDF é a fonte; em caso de divergência, prevalece o PDF.
> - As 5 passagens reconstruídas do original foram confirmadas pelo owner (D-16).
> - Os elementos gráficos não foram verificados visualmente; estão marcados com `TODO(owner)`.
> - A atribuição de algumas listas aos seus títulos é inferida a partir do layout em colunas (A-22).

**Visão do produto, módulos funcionais, arquitectura e roadmap de engenharia**

OBSERVE · LEARN · UNDERSTAND · ANTICIPATE · EXECUTE

Elaborado por André Vasconcelos Kanhanga, Engenheiro de Software. Documento de visão e referência para o desenvolvimento do KAI · V1.0 · 20 de Novembro de 2026.

<!-- TODO(owner): a capa (p.1) tem elementos gráficos ("KAI-CORE // ONLINE") não verificados visualmente. -->

---

## 00 · Sobre este documento (p.2)

Este documento consolida a visão inicial do KAI: um assistente pessoal inteligente, multimodal e extensível, concebido para ligar o utilizador a conhecimento, ferramentas, aplicações, dados e dispositivos através de linguagem natural, voz e interfaces visuais.

Serve como ponto de partida para o Product Discovery, o desenho técnico e a implementação incremental. Não pretende que todos os componentes sejam implementados na primeira versão.

| Campo | Valor |
|---|---|
| Produto | KAI, a marca e o ecossistema tecnológico |
| Nome da inteligência | KAI |
| Categoria | Personal AI Intelligence System |
| Objectivo inicial | Assistente pessoal para uso próprio, com possibilidade de evolução multiutilizador |
| Estratégia arquitectural | Modular Monolith + serviços especializados extraídos quando justificado |
| Stack principal | React + TypeScript, Laravel, Python, MySQL, RabbitMQ, Redis |
| Público inicial | Utilizador individual / ambiente de desenvolvimento próprio |
| Estado | Product Discovery, proposta inicial |

**Princípio orientador:** construir um produto que seja útil no dia-a-dia e, simultaneamente, um laboratório de engenharia de software, AI engineering, sistemas distribuídos, DevOps, segurança e observabilidade.

**Como ler este documento:**
- A **visão** descreve o produto que pretendemos alcançar.
- Os **módulos** descrevem capacidades funcionais da aplicação.
- A **arquitectura** descreve os limites e as responsabilidades técnicas.
- O **roadmap** define uma sequência incremental de entregas.
- As decisões ainda não confirmadas devem ser fechadas durante o Product Discovery.

## Índice (p.3)

1. Visão e posicionamento do produto
2. Princípios de produto e engenharia
3. Pilares fundamentais
4. Módulos funcionais
5. Arquitectura lógica e microsserviços
6. Motor de inteligência e ciclo de execução
7. Agentes, missões e ferramentas
8. Dados, memória e conhecimento
9. Interface e experiência de utilização
10. Desktop Agent e ambiente local
11. Segurança, privacidade e governação
12. Observabilidade e fiabilidade
13. Stack tecnológica
14. Estrutura proposta do monorepo
15. CI/CD e deployment
16. Roadmap de desenvolvimento
17. Cenários de demonstração e critérios de qualidade
18. Estratégia de publicação no GitHub
19. Decisões pendentes de Product Discovery

> **Nota:** a estrutura e as tecnologias apresentadas são uma proposta inicial. A implementação deverá validar compatibilidade, custos, requisitos de segurança e necessidade real de cada componente.

---

## 01 · Visão e posicionamento do produto (p.4)

- **KAI** será a marca e o ecossistema tecnológico.
- **KAI** será a inteligência com quem o utilizador interage.
- **KAI Core** será o núcleo responsável por compreender pedidos, gerir contexto, planear tarefas, seleccionar agentes e coordenar ferramentas.

A inteligência deverá compreender linguagem natural, manter contexto, pesquisar informação, analisar dados, utilizar ferramentas e executar operações autorizadas.

A ambição é criar uma camada inteligente entre o utilizador e o seu ecossistema digital, reduzindo a fragmentação entre aplicações de produtividade, desenvolvimento, documentos, dados e infraestrutura.

> **Declaração de visão:** Criar uma inteligência pessoal que compreenda o contexto do utilizador e execute operações autorizadas, mantendo-o sempre informado e no controlo.

**Problemas que pretende resolver:**
- Fragmentação do trabalho entre múltiplas aplicações e serviços.
- Repetição de tarefas manuais e fluxos operacionais.
- Dificuldade em recuperar contexto disperso em conversas e documentos.
- Necessidade de interpretar dados, logs, código e informação visual.
- Falta de uma interface única para consultar e coordenar ferramentas autorizadas.

**Posicionamento:** KAI posiciona-se como uma plataforma pessoal de inteligência que integra conversação, memória, agentes, ferramentas, workflows, análise e integração com o ambiente local.

## 02 · Princípios de produto e engenharia (p.5)

**Princípios de produto:**
- **Utilidade antes da complexidade:** cada funcionalidade deve resolver uma necessidade real.
- **Human-in-the-loop:** o utilizador mantém controlo sobre operações relevantes.
- **Transparência:** KAI deve explicar fontes, limitações, acções e resultados.
- **Memória controlável:** o utilizador pode consultar, corrigir e eliminar informação persistente.
- **Extensibilidade:** novas ferramentas e agentes devem poder ser adicionados por contratos definidos.
- **Privacidade por desenho:** recolher e partilhar apenas os dados necessários.

**Princípios de engenharia:**
- Começar com um Modular Monolith no Core.
- Separar responsabilidades por domínios e contratos.
- Extrair microsserviços apenas quando existir benefício operacional ou de escala.
- Utilizar eventos e filas para tarefas assíncronas.
- Instrumentar os serviços desde o início.
- Testar regras de negócio, integrações, segurança e comportamento dos agentes.
- Documentar decisões arquitecturais através de ADRs.

**Não-objectivos iniciais:**
- ✕ Treinar um modelo de linguagem de raiz.
- ✕ Criar uma arquitectura com muitos microsserviços antes de existir necessidade.
- ✕ Dar ao modelo acesso irrestrito ao sistema operativo, bases de dados ou ficheiros.
- ✕ Implementar automações sensíveis sem aprovação e auditoria.
- ✕ Optimizar para escala massiva antes de validar o produto.

## 03 · Pilares fundamentais (p.5)

| Pilar | Âmbito |
|---|---|
| Intelligence | Raciocínio, planeamento, selecção de agentes e avaliação de resultados. |
| Memory | Contexto de sessão, histórico, conhecimento semântico e recuperação. |
| Communication | Texto, voz, streaming e entradas multimodais. |
| Automation | Ferramentas, integrações, missões e workflows. |
| Environment | Desktop, aplicações, ficheiros e dispositivos autorizados. |
| Data Intelligence | Análise de dados, visualização, métricas e relatórios. |
| Security | Identidade, permissões, aprovações, isolamento e auditoria. |
| Observability | Logs, métricas, traces, alertas e fiabilidade. |

Estes pilares são transversais: por exemplo, uma missão de análise de código utiliza Intelligence, Memory, Tools, Security e Observability ao mesmo tempo.

## 04 · Módulos funcionais (p.6)

| # | Módulo | Propósito | Capacidades |
|---|---|---|---|
| 4.1 | KAI Command Center | Interface principal para interacção e acompanhamento. | Conversação por texto e voz; núcleo visual animado; histórico; estado dos agentes; missões activas; notificações; actividades recentes; indicadores de utilização. |
| 4.2 | Conversational Intelligence | Gestão da comunicação entre utilizador e KAI. | Streaming de respostas; contexto conversacional; suporte a português e inglês; pesquisa no histórico; análise de imagens e documentos; respostas com referências e indicação de limitações. |
| 4.3 | Voice Intelligence | Experiência de conversação por voz. | Speech-to-Text; Text-to-Speech; sessões de voz; detecção de fim de fala; interrupção de respostas; activação por botão; wake word numa fase posterior. |
| 4.4 | Memory & Knowledge Management | Gestão transparente de contexto e conhecimento. | Working Memory; Conversation Memory; Long-Term Memory; memória episódica, semântica e procedural; indexação documental; embeddings; pesquisa semântica; RAG; controlo de retenção. |
| 4.5 | Agent Management | Registo, configuração e monitorização de agentes especializados. | Identidade; instruções; modelo; ferramentas; permissões; limites; memória; versões; histórico; métricas e avaliação. |
| 4.6 | Tools & Integrations | Catálogo de conectores e ferramentas autorizadas. | GitHub; GitLab; Docker; calendários; email; documentos; bases de dados autorizadas; APIs; webhooks; MCP. |
| 4.7 | Automation & Workflow Engine | Criação e execução de processos automatizados. | Editor visual; triggers; condições; acções; agendamento; webhooks; execução assíncrona; retry; histórico; integração com agentes. |
| 4.8 | Developer Intelligence | Assistência a actividades de engenharia de software. | Análise de repositórios; explicação de código; análise de dependências; propostas de refactoring; geração de testes; leitura de logs; revisão de pipelines e documentação. |
| 4.9 | System & Environment Intelligence | Consulta e diagnóstico de ambientes tecnológicos autorizados. | Estado de containers; logs; CPU; memória; estado de serviços; disponibilidade de APIs; alertas e histórico operacional. |
| 4.10 | Data Intelligence | Análise de dados estruturados e produção de relatórios. | Importação CSV/Excel; análise exploratória; estatísticas; consultas autorizadas; gráficos; detecção de anomalias; previsões e relatórios. |
| 4.11 | Vision & Multimodal Intelligence | Interpretação de informação visual e documental. | OCR; imagens; screenshots; gráficos; diagramas; extracção documental e comparação visual. |
| 4.12 | Security & Governance | Controlo de identidade, autorização e rastreabilidade. | Autenticação; MFA; RBAC; permissões por ferramenta; aprovações; auditoria; gestão de segredos; limites de utilização; isolamento de utilizadores. |

## 05 · Arquitectura lógica e microsserviços (p.7–8)

A arquitectura inicial deverá separar o cliente, o Core de negócio, o motor de inteligência, a infraestrutura de mensagens, os dados e as integrações externas.

**Camadas principais:**

| Camada | Responsabilidade | Tecnologias propostas |
|---|---|---|
| Client Applications | Web, desktop e futuramente mobile | React, TypeScript, Vite, Tauri |
| API / Realtime Gateway | APIs, autenticação, streaming e autorização | Laravel, REST, Reverb/WebSockets |
| Core Platform | Utilizadores, conversas, agentes, ferramentas, missões e auditoria | Laravel modular |
| AI Intelligence | Orquestração, runtime, RAG, speech e vision | Python, FastAPI |
| Messaging | Eventos, comandos e processamento assíncrono | RabbitMQ, Redis |
| Persistence | Dados transaccionais, vetores e ficheiros | MySQL, Qdrant, MinIO |
| Observability | Métricas, logs e traces | Prometheus, Grafana, Loki, Tempo, OpenTelemetry |

**Diagrama de camadas (p.7), transcrição do texto:**
- CLIENT APPLICATIONS
- API / REALTIME GATEWAY
- CORE PLATFORM: Laravel modular (Modular Monolith); utilizadores · conversas · agentes; ferramentas · missões · auditoria
- AI INTELLIGENCE: Python · FastAPI (AI Engine); orquestração · agentes · RAG; speech · vision · LLM Gateway
- MESSAGING
- PERSISTENCE

<!-- TODO(owner): o diagrama da p.7 não foi verificado visualmente; as caixas MESSAGING e PERSISTENCE aparecem sem conteúdo no texto extraído e a camada Observability não aparece no diagrama (A-12). -->

**Microsserviços candidatos à extracção (p.8):**

| Serviço | Responsabilidade | Tecnologia provável |
|---|---|---|
| AI Orchestrator | Planeamento e coordenação da inteligência | Python |
| Agent Runtime | Execução isolada de agentes | Python |
| LLM Gateway | Abstracção de fornecedores e modelos | Python |
| Memory Service | Indexação, recuperação e memória semântica | Python |
| Speech Service | Processamento STT/TTS | Python |
| Vision Service | OCR e processamento multimodal | Python |
| Tool Execution | Execução controlada de ferramentas | Python |
| Document Processing | Extracção e processamento de documentos | Python |
| Notification Worker | Notificações assíncronas | Laravel / Python |
| Analytics Worker | Agregações e análises | Python |

> **Regra arquitectural:** começar com Laravel como **Modular Monolith** e um **AI Engine Python** separado. Extrair novos serviços quando houver necessidade de escalabilidade independente, isolamento, tecnologia específica, frequência de deployment ou limites operacionais distintos.

## 06 · Motor de inteligência e ciclo de execução (p.9)

O KAI Core deverá coordenar a interpretação do pedido, a construção de contexto, o planeamento, a selecção de agentes, a autorização de ferramentas, a execução e a avaliação dos resultados.

| # | Etapa | Descrição |
|---|---|---|
| 01 | Input | Recebe texto, áudio, imagem, documento ou evento. |
| 02 | Context Builder | Reúne contexto da conversa, memória relevante e permissões. |
| 03 | Intent & Planning | Interpreta o objectivo e cria um plano de execução. |
| 04 | Agent Selection | Selecciona o agente ou conjunto de agentes adequado. |
| 05 | Tool Selection | Identifica ferramentas e valida permissões e políticas. |
| 06 | Execution | Executa operações permitidas, síncronas ou assíncronas. |
| 07 | Result Evaluation | Verifica resultados, erros, evidências e consistência. |
| 08 | Response Generation | Produz resposta estruturada e comunica o estado. |
| 09 | Memory Update | Actualiza apenas memórias elegíveis segundo as políticas. |

O motor deverá suportar tarefas de uma única etapa e missões com múltiplas etapas. A execução deve ser observável, cancelável quando possível, limitada por tempo e recursos, e recuperável perante falhas.

**Abordagem de implementação** (atribuição inferida pelo layout):
- Criar contratos próprios para Agent, Tool, Mission e Execution.
- Separar planeamento de execução.
- Manter validação de permissões fora do LLM.
- Validar entradas e saídas de cada ferramenta.
- Guardar eventos e resultados relevantes.
- Utilizar workflows explícitos para tarefas previsíveis e agentes para tarefas que exigem interpretação.

## 07 · Agentes, missões e ferramentas (p.9–10)

**Agentes iniciais propostos:**

| Agente | Responsabilidade |
|---|---|
| Orchestrator Agent | Coordena pedidos, contexto e delegação. |
| Research Agent | Pesquisa, compara fontes e prepara relatórios. |
| Developer Agent | Analisa código, repositórios e testes. |
| DevOps Agent | Consulta ambientes, logs, containers e deployments. |
| Data Analyst Agent | Analisa dados, gráficos e tendências. |
| Document Agent | Lê, classifica, resume e produz documentos. |
| Productivity Agent | Organiza tarefas, agenda e actividades. |
| Security Agent | Analisa configurações, dependências e alertas. |
| Vision Agent | Interpreta imagens, screenshots e informação visual. |

Um agente é uma entidade lógica com instruções, ferramentas, permissões e objectivos próprios. Não implica necessariamente um modelo diferente por agente; vários agentes poderão partilhar fornecedores e modelos.

**Entidade Mission:** uma Mission representa uma unidade de trabalho com objectivo, plano, passos, agentes, ferramentas, estado, progresso, aprovações, resultados e eventos.

Fluxo principal: PENDING › PLANNING › RUNNING › AWAITING APPROVAL › COMPLETED

| Estado | Significado |
|---|---|
| PENDING | A missão foi criada e aguarda processamento. |
| PLANNING | O plano está a ser elaborado. |
| RUNNING | A execução está em curso. |
| AWAITING_APPROVAL | Uma operação aguarda autorização. |
| PAUSED | A missão foi suspensa. |
| COMPLETED | A missão foi concluída. |
| FAILED | A missão falhou. |
| CANCELLED | A missão foi cancelada. |

**Tool Registry:**
- Nome, descrição, categoria e versão.
- JSON Schema de entrada e saída.
- Permissões necessárias.
- Modo de execução: `read-only`, `draft` ou `write`.
- Timeout, retry e limites.
- Política de aprovação.
- Auditoria e estado de disponibilidade.

## 08 · Dados, memória e conhecimento (p.11)

**Armazenamento por responsabilidade:**

| Tecnologia | Utilização |
|---|---|
| MySQL 8 | Dados relacionais e transaccionais: utilizadores, conversas, missões, agentes, ferramentas e auditoria. |
| Redis | Cache, sessões, rate limiting e coordenação temporária. |
| Qdrant | Embeddings, pesquisa vetorial e recuperação semântica. |
| MinIO | Object storage para documentos, áudio, imagens e ficheiros. |
| RabbitMQ | Mensagens, eventos e processamento assíncrono. |

**Entidades centrais preliminares:**

| Domínio | Entidades |
|---|---|
| Conversação | users, user_preferences, sessions, conversations, messages, attachments |
| Agentes | agents, agent_versions, agent_tools, agent_permissions |
| Missões | missions, mission_steps, mission_events, mission_approvals |
| Ferramentas | tools, tool_versions, tool_executions |
| Conhecimento | memories, knowledge_sources, knowledge_documents, document_chunks |
| Integrações | integrations, integration_credentials, webhooks |
| Workflows | workflows, workflow_versions, workflow_executions |
| Plataforma | notifications, audit_logs, model_providers, model_usage |

**Princípios de dados** (atribuição inferida pelo layout):
- MySQL mantém a fonte de verdade transaccional.
- Qdrant guarda representações vectoriais, não substitui a base relacional.
- MinIO armazena os binários e MySQL guarda metadados e referências.
- Memórias persistentes devem ter origem, data, política de retenção e possibilidade de revisão.
- A indexação documental deve ser assíncrona e idempotente.
- Dados de utilizadores diferentes devem permanecer isolados.

**Memória e RAG:** o pipeline documental deverá incluir as seguintes etapas, com as permissões de acesso aplicadas também durante a recuperação:

INGESTÃO › VALIDAÇÃO › EXTRACÇÃO › LIMPEZA › CHUNKING › EMBEDDINGS › INDEXAÇÃO › RECUPERAÇÃO › RERANKING\* › RESPOSTA COM FONTES

\* Quando necessário.

> Nota posterior (não faz parte do PDF): o MinIO foi arquivado a 2026-04-25 e foi substituído pelo SeaweedFS via API S3 (D-12, ADR-0008). O MySQL fica fixado na 8.4 LTS (D-09).

## 09 · Interface e experiência de utilização (p.12)

A aplicação deverá oferecer uma experiência **dark-first, minimalista e futurista**, com prioridade para clareza, acessibilidade e produtividade.

**Navegação proposta:**

| Área | Conteúdo |
|---|---|
| Command Center | Visão geral, interacção, estado do sistema e actividade. |
| Conversations | Conversas, pesquisa e histórico. |
| Missions | Missões, progresso, passos e aprovações. |
| AI Agents | Agentes, configurações, ferramentas e métricas. |
| Knowledge | Memórias, documentos, fontes e pesquisa. |
| Automations | Workflows, triggers e execuções. |
| Developer Tools | Repositórios, código, APIs e análises. |
| System Monitor | Containers, serviços, logs e métricas. |
| Integrations | Conectores, credenciais e permissões. |
| Analytics | Utilização, custos, desempenho e qualidade. |
| Security & Audit | Sessões, permissões, aprovações e histórico. |
| Settings | Preferências, modelos, voz e configurações. |

**Estados visuais do núcleo KAI:**

| Estado | Representação |
|---|---|
| Idle | A aguardar interacção. |
| Listening | A captar voz. |
| Processing | A interpretar e preparar resposta. |
| Executing | A executar uma ferramenta ou missão. |
| Speaking | A responder por voz. |
| Awaiting approval | A aguardar autorização do utilizador. |
| Error | A apresentar falha ou limitação. |

**Stack de interface:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Framer Motion e, quando justificado, Three.js / React Three Fiber para elementos 3D.

## 10 · Desktop Agent e ambiente local (p.13)

Numa fase posterior, KAI terá uma aplicação desktop, preferencialmente avaliada com **Tauri + React**. O desktop permitirá interagir com o ambiente local sem transformar o assistente num executor irrestrito do sistema operativo.

**Capacidades previstas** (atribuição inferida pelo layout):
- Janela flutuante e atalho global configurável.
- Notificações nativas e sessões de voz.
- Acesso a ficheiros seleccionados pelo utilizador.
- Consulta de aplicações e serviços autorizados.
- Monitorização local de serviços e containers.
- Execução de ferramentas locais com permissões explícitas.
- Comunicação autenticada com a plataforma central.

**Arquitectura local:** LOCAL DESKTOP AGENT ▼ PERMISSION & POLICY LAYER ▼ APPROVED LOCAL TOOLS ▼ LOCAL ENVIRONMENT

> **Menor privilégio:** o agente local deve operar com princípio de menor privilégio. Acesso a ficheiros, execução de comandos e alterações no ambiente devem ser delimitados, confirmados quando necessário e registados.

## 11 · Segurança, privacidade e governação (p.13–14)

A segurança deve ser transversal a todos os módulos. **O modelo de linguagem não é uma fronteira de segurança** e não pode decidir, por si só, que uma operação está autorizada.

**Níveis de operação:**

| Nível | Tipo | Política proposta |
|---|---|---|
| 1 | Consulta de informação autorizada | Permitida após verificação de acesso. |
| 2 | Análise e relatórios | Permitida dentro do escopo autorizado. |
| 3 | Criação de rascunhos | Permitida; não envia nem publica automaticamente. |
| 4 | Alteração de dados ou ficheiros | Aprovação conforme risco e política. |
| 5 | Operações sensíveis | Confirmação explícita e auditoria. |
| 6 | Operações proibidas | Bloqueadas pela política do sistema. |

**Controlos de segurança** (atribuição inferida pelo layout):
- Autenticação segura, MFA e gestão de sessões.
- RBAC e permissões por recurso, agente e ferramenta.
- Gestão de segredos fora do código e das mensagens.
- Encriptação em trânsito e em repouso.
- Isolamento de ferramentas e limites de execução.
- Protecção contra prompt injection e conteúdo não confiável.
- Validação de schemas de entrada e saída.
- Rate limiting, quotas e limites de custo.
- Auditoria de operações e aprovações.
- Políticas de retenção, exportação e eliminação de dados.

> **Regra para fontes externas:** documentos, emails, páginas e repositórios são fontes de dados **não confiáveis**. Instruções encontradas nesses conteúdos não podem sobrepor-se às políticas, permissões ou instruções de sistema do KAI.

## 12 · Observabilidade e fiabilidade (p.14–15)

A observabilidade deve permitir acompanhar uma operação desde a interface até ao Core, motor de IA, filas, ferramentas e serviços externos.

| Tecnologia | Responsabilidade |
|---|---|
| OpenTelemetry | Instrumentação e propagação de traces. |
| Prometheus | Recolha e consulta de métricas. |
| Grafana | Dashboards e alertas. |
| Loki | Agregação e consulta de logs. |
| Tempo | Armazenamento e consulta de traces. |

**Indicadores a acompanhar:**

| Domínio | Indicadores |
|---|---|
| Aplicação | Latência, throughput, erros, disponibilidade e consumo. |
| IA | Latência dos modelos, tokens, custos, falhas de agentes e tool calls. |
| RabbitMQ | Mensagens pendentes, throughput, consumidores, rejeições e DLQ. |
| Dados | Latência de queries, conexões, falhas e utilização de armazenamento. |
| Infraestrutura | CPU, memória, disco, rede e estado dos containers. |
| Qualidade | Sucesso de missões, qualidade de recuperação e resultados de avaliação. |

**Padrões de resiliência** (atribuição inferida pelo layout):
- Timeouts explícitos e limites de concorrência.
- Retry com backoff e jitter para falhas transitórias.
- Dead Letter Queues para mensagens não processáveis.
- Idempotência em consumidores e operações repetíveis.
- Circuit Breaker para dependências instáveis.
- Transactional Outbox para publicação fiável de eventos.
- Health checks e graceful shutdown.

## 13 · Stack tecnológica (p.15–16)

| Camada | Tecnologia proposta |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI / Styling | Tailwind CSS + shadcn/ui |
| Animações / 3D | Framer Motion; Three.js / React Three Fiber |
| Backend Core | Laravel 12 / PHP 8.3+ como baseline inicial a validar |
| AI Engine | Python + FastAPI |
| LLM Providers | Abstracção de fornecedores; APIs externas e modelos locais |
| Local AI | Ollama para experimentação e execução local |
| Relational Database | MySQL 8 |
| Vector Database | Qdrant |
| Cache | Redis |
| Message Broker | RabbitMQ |
| Object Storage | MinIO |
| Realtime | Laravel Reverb / WebSockets |
| Desktop | Tauri + React |
| Containers | Docker + Docker Compose |
| Reverse Proxy | Nginx |
| CI/CD | GitHub Actions |
| PHP Testing | Pest / PHPUnit |
| Frontend Testing | Vitest + Playwright |
| Python Testing | Pytest |
| Static Analysis | PHPStan / Larastan; mypy ou equivalente |
| Monitoring | Prometheus + Grafana |
| Logs / Traces | Loki + OpenTelemetry + Tempo |

As versões exactas serão fixadas no início da implementação, após validação de compatibilidade, manutenção, licenciamento e requisitos do ambiente.

> Nota posterior (não faz parte do PDF): baseline validada a 2026-11-20 — Laravel 13 · PHP 8.5 · MySQL 8.4 LTS · Python 3.14 · RabbitMQ 4.4 · Redis 8 (ADR-0007).

## 14 · Estrutura proposta do monorepo (p.16)

```
KAI/
├── apps/
│   ├── web/                    # React + TypeScript
│   ├── desktop/                # Tauri + React (fase posterior)
│   ├── api/                    # Laravel Core
│   └── ai-engine/              # Python + FastAPI
├── services/
│   ├── document-processing/
│   ├── notification-worker/
│   └── analytics-worker/
├── packages/
│   ├── contracts/
│   ├── typescript-sdk/
│   ├── ui/
│   └── shared-config/
├── infrastructure/
│   ├── docker/    ├── nginx/      ├── rabbitmq/
│   ├── redis/     ├── qdrant/     ├── prometheus/
│   └── grafana/   ├── loki/       └── tempo/
├── docs/
│   ├── architecture/   ├── adr/        ├── api/
│   ├── database/       ├── security/   ├── operations/
│   └── product/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
├── Makefile
└── README.md
```

> **Crescimento incremental:** a estrutura deverá crescer de forma incremental. Não criar pastas ou serviços vazios para antecipar uma arquitectura que ainda não foi validada.

## 15 · CI/CD e deployment (p.17)

**Pipeline proposto:** PUSH / PR › CODE QUALITY › TESTS › BUILD › SECURITY SCAN › PUBLISH › DEPLOY › POST-DEPLOY

| Etapa | Verificações e actividades |
|---|---|
| Push / Pull Request | Início automático do pipeline. |
| Code Quality | Lint, formatting, análise estática e validação de tipos. |
| Automated Tests | Unitários, integração, arquitectura e E2E. |
| Build | Build do frontend, backend e imagens Docker. |
| Security Scan | Dependências, imagens, segredos e SBOM. |
| Artifact Publishing | Publicação de imagens versionadas. |
| Deployment | Desenvolvimento, staging e produção. |
| Post-deployment | Health checks, smoke tests e monitorização. |

**Estratégia de ambientes** (atribuição inferida pelo layout):
- Desenvolvimento local com Docker Compose.
- Staging para validar integração e migrations.
- Produção com configuração, segredos e dados separados.
- Backups e testes de recuperação.
- Migrations controladas e estratégia de rollback.
- Kubernetes apenas se a escala e a operação justificarem.

## 16 · Roadmap de desenvolvimento (p.17–18)

| # | Milestone | Âmbito |
|---|---|---|
| 01 | Product Discovery | PRD, casos de uso, requisitos, C4, domínios, ADRs e identidade visual. |
| 02 | Core Foundation | Monorepo, Docker, Laravel, React, MySQL, autenticação e contratos. |
| 03 | KAI Intelligence | Python AI Engine, LLM Gateway, conversação, streaming e contexto. |
| 04 | Memory System | Histórico, memória configurável, Qdrant, embeddings, RAG e documentos. |
| 05 | Agent Framework | Agent Registry, runtime, Tool Registry, missions e avaliação. |
| 06 | Voice Experience | STT, TTS, sessões de voz, interrupção e interface de áudio. |
| 07 | Integrations & Automation | GitHub, Docker, APIs, webhooks, RabbitMQ e workflow engine. |
| 08 | Advanced Intelligence | Vision, analytics, developer intelligence e system intelligence. |
| 09 | Distributed Architecture | Serviços extraídos, eventos, Outbox, retry, DLQ e idempotência. |
| 10 | Production Readiness | Observabilidade, CI/CD, segurança, carga, desktop e documentação. |

Cada milestone deve terminar com uma entrega funcional, testes, documentação e critérios de aceitação. A duração será estimada depois da decomposição em épicos e tarefas.

> Nota posterior (não faz parte do PDF): a CI foi antecipada para o M02, e o RabbitMQ, o Outbox e o OpenTelemetry para o M03 (D-11, ADR-0011).

## 17 · Cenários de demonstração e critérios de qualidade (p.18–19)

| Cenário | Demonstração esperada |
|---|---|
| Daily Briefing | Consultar fontes autorizadas e apresentar prioridades do dia. |
| Research Mission | Pesquisar, comparar fontes e produzir relatório com referências. |
| Developer Assistant | Analisar repositório e propor melhorias com evidências. |
| Docker Intelligence | Consultar containers, logs e métricas de ambiente autorizado. |
| Document Intelligence | Indexar PDFs e responder com referências às fontes. |
| Data Analyst | Analisar Excel/CSV e produzir gráficos e indicadores. |
| Workflow Automation | Criar e executar fluxo com histórico e tratamento de falhas. |
| Voice Interaction | Conversar por voz com interrupção e contexto. |
| Multi-Agent Collaboration | Coordenar agentes numa missão com responsabilidades distintas. |
| System Diagnosis | Analisar logs e métricas e produzir diagnóstico fundamentado. |

**Métricas de qualidade:**

| Métrica | Objectivo de medição |
|---|---|
| Task Success Rate | Percentagem de missões concluídas com sucesso. |
| Tool Success Rate | Taxa de execução bem-sucedida das ferramentas. |
| Response Latency | Tempo de resposta por tipo de tarefa. |
| Retrieval Quality | Relevância e precisão da recuperação documental. |
| Groundedness | Proporção de afirmações suportadas por fontes. |
| Cost per Task | Custo estimado por missão. |
| Error Rate | Taxa de falhas por serviço e operação. |
| Availability | Disponibilidade do sistema e dependências. |

> **Avaliação de IA:** as avaliações de IA devem utilizar conjuntos de testes versionados e critérios repetíveis, não apenas avaliações subjectivas durante demonstrações.

## 18 · Estratégia de publicação no GitHub (p.19)

O repositório público deverá demonstrar o produto e a qualidade da engenharia, sem expor credenciais, dados pessoais, chaves, configurações sensíveis ou integrações privadas.

**Conteúdo recomendado:**
- README em inglês com visão, funcionalidades e quick start.
- Diagramas C4, sequência e arquitectura de deployment.
- Modelo de domínio e documentação de dados.
- ADRs com decisões e alternativas.
- OpenAPI e contratos de eventos.
- Documentação dos agentes e ferramentas.
- Docker Compose e instruções de instalação.
- Testes automatizados e workflows CI.
- Screenshots e vídeo de demonstração.
- Roadmap público, licença e política de segurança.

> Nota posterior (não faz parte do PDF): o owner decidiu escrever o repositório todo em PT-PT, incluindo o README (D-01, ADR-0012).

**Licença e publicação:** a licença deverá ser escolhida conscientemente antes da publicação. Verificar licenças das dependências, modelos, datasets e assets. Usar dados sintéticos no ambiente de demonstração e disponibilizar ficheiros de configuração de exemplo sem segredos.

## 19 · Decisões pendentes de Product Discovery (p.20)

As seguintes decisões devem ser confirmadas antes de fechar a arquitectura detalhada e iniciar a implementação:

| Decisão | Opções a avaliar | Recomendação inicial |
|---|---|---|
| Deployment | Local, cloud ou híbrido | Local em desenvolvimento; cloud para produção. |
| Modelos IA | Cloud, local ou híbrido | Híbrido, com provider abstraction. |
| Público | Pessoal, multiutilizador ou SaaS | Pessoal primeiro; preparar evolução. |
| Prioridade | Engenharia, experiência ou IA | Equilíbrio entre produto e engenharia. |
| Desktop | Agora ou fase posterior | Fase posterior, após validar Web. |
| Wake word | Activação por botão ou palavra-chave | Botão primeiro; wake word depois. |
| Microsserviços | Desde o início ou evolução | Modular Monolith + extracção selectiva. |

**Perguntas técnicas a resolver:**
1. Qual fornecedor de LLM será utilizado no primeiro protótipo?
2. Qual será a estratégia de STT e TTS e o respectivo custo?
3. Que dados e documentos poderão ser indexados?
4. Quais ferramentas terão acesso local e quais serão apenas cloud?
5. Qual será o mecanismo de autenticação entre serviços?
6. Como serão versionados os contratos e eventos?
7. Quais são os limites de custo, latência e execução por missão?

**Como arrancar o desenvolvimento:** o desenvolvimento deverá começar pela leitura e validação deste documento, não pela geração imediata de toda a aplicação. O trabalho deve avançar em iterações pequenas, verificáveis e documentadas.

**Sequência inicial recomendada:**
1. Criar o repositório KAI.
2. Adicionar este documento à pasta `docs/product/` como referência do produto.
3. Registar dúvidas e ambiguidades encontradas na leitura.
4. Produzir PRD detalhado e requisitos não funcionais.
5. Criar diagramas C4 e ADRs iniciais.
6. Definir bounded contexts e contratos entre Laravel e Python.
7. Só depois criar a estrutura inicial do monorepo e Docker Compose.

## Prompt de arranque para o assistente de desenvolvimento (p.21)

> Estamos a iniciar o KAI, um Personal AI Intelligence System. Lê integralmente o documento `docs/product/kai_Product_Vision_Architecture_Roadmap.pdf` (ou a versão Markdown equivalente) antes de propor alterações. Nesta primeira tarefa, NÃO implementes código. Actua como Software Architect e Product Engineer:
> 1. Resume a visão e os limites do produto.
> 2. Identifica requisitos funcionais e não funcionais.
> 3. Identifica ambiguidades, riscos e decisões pendentes.
> 4. Propõe bounded contexts e responsabilidades do Laravel Core e Python AI Engine.
> 5. Propõe os primeiros ADRs.
> 6. Define um MVP pequeno com critérios de aceitação.
> 7. Apresenta um plano de implementação incremental.
>
> Não inventes requisitos. Distingue decisões confirmadas de hipóteses. Prioriza simplicidade, segurança, testabilidade e evolução arquitectural. Aguarda aprovação antes de criar ou alterar ficheiros.

<!-- TODO(owner): o nome de ficheiro referido no prompt (kai_Product_...pdf) difere do ficheiro real (1_KAI_Product_...pdf), ver A-23 / P-001. -->

**Definição de pronto (Definition of Done):**
- ✓ O requisito está documentado e tem critérios de aceitação.
- ✓ A implementação respeita os limites de domínio e os contratos.
- ✓ Existem testes adequados e passam localmente.
- ✓ Logs e erros são tratados sem expor dados sensíveis.
- ✓ A documentação foi actualizada.
- ✓ A alteração foi revista antes de integrar.

> **Regra de trabalho:** trabalhar em pequenas entregas. Antes de cada implementação, compreender o requisito; depois, propor plano; só então implementar, testar e documentar. Cada decisão relevante deve ter justificação.
