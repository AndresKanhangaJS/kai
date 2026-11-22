# SPEC-002: Identity & Access — login por passkey/TOTP e gestão de sessões

- **Estado:** Aprovada (2026-11-20)
- **Data:** 2026-11-20
- **Milestone:** M02
- **Autor:** Claude Code (`kai-spec`), revisão do owner pendente
- **Requisitos:** FR-044, FR-045, FR-051; NFR-002, NFR-007, NFR-008, NFR-009
- **ADRs relacionados:** ADR-0013 (modelo de segurança, re-autenticação de nível 5); D-05 (`analysis.md` §0)

## 1. Contexto
- **[C D-05]** O owner autentica-se por passkey (WebAuthn) ou TOTP, com códigos de recuperação; re-autenticação exigida nos últimos 10 min para operações de nível 5; a conta é criada por CLI, sem registo público.
- **[C FR-044, FR-045]** Autenticação por passkey + TOTP; MFA e gestão de sessões (listar e revogar) entram no MVP.
- **[C P-017, fechada]** `laravel/fortify` v1.43.0 + `laravel/passkeys` v0.3.0 (MIT) já instalados em `apps/api` (E4.1); cobrem WebAuthn e TOTP (`pragmarx/google2fa`) num só pacote oficial.
- **[H]** Esta spec cobre só Identity & Access; não repete AC-01, AC-03 a AC-10 (`docs/specs/001-mvp-fatia-vertical.md`), só aprofunda a AC-02.
- **[C, descoberto na E4.5]** O `laravel/fortify` trata o TOTP como **segundo factor depois de uma password** (o desafio de 2FA só é alcançável depois do `/login` com password). Como não há password (D-05), isto exigiu um controlador próprio (`TotpLoginController`) que reutiliza a verificação do Fortify mas entra directamente por email+código, sem o passo de password.

## 2. Objectivo
O owner autentica-se de forma *phishing-resistant* (passkey) ou com TOTP como alternativa, gere as suas sessões activas e pode revogar qualquer uma; uma sessão revogada deixa imediatamente de autenticar pedidos.

## 3. Critérios de aceitação

| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-02a | O owner criado por CLI, com uma passkey registada | Faz login com essa passkey | Obtém uma sessão autenticada; o evento fica auditado | E2E (ver nota) |
| AC-02b | O owner sem a passkey disponível (ex. noutro dispositivo) | Faz login com um código TOTP válido | Obtém uma sessão autenticada | integração |
| AC-02c (negativo) | Um código TOTP inválido ou expirado | O owner tenta autenticar-se | A autenticação falha; nenhuma sessão é criada; a tentativa fica auditada | integração, negativo |
| AC-02d | O owner autenticado, com várias sessões activas | Lista as suas sessões | Vê cada uma com dispositivo, IP e data da última actividade, sem dados de outra pessoa (não há outra, mas a query já filtra por `user_id`) | integração |
| AC-02e | O owner autenticado, com uma sessão noutro dispositivo | Revoga essa sessão (não a actual) | Essa sessão deixa de autenticar pedidos a partir desse momento | integração |
| AC-02f (negativo, núcleo da AC-02) | Uma sessão revogada | Chega um pedido com o identificador dessa sessão | É rejeitado (401), sem aceder a nenhum recurso nem executar nenhuma lógica de negócio | integração, negativo |
| AC-02g | O owner sem acesso a passkey nem TOTP | Usa um código de recuperação válido | Obtém uma sessão autenticada; esse código fica invalidado (uso único) | integração |

## 4. Segurança e privacidade

- **Níveis de operação:** login, listagem e revogação de sessão são acções do Core Platform, autenticadas directamente no **PEP-1** (gateway Laravel); não passam pelo Tool Registry nem pelos níveis 1–6 do ADR-0013 (esses aplicam-se à execução de ferramentas por um agente). A sessão resultante grava `last_authenticated_at`, campo que o M05 vai usar para exigir re-autenticação em operações de nível 5 (D-05) — **o campo entra agora, a exigência não** (fora de âmbito, §8).
- **Dados tocados e isolamento:** `users`, `sessions` (schema a definir em E4.3). Toda a query de sessões filtra por `user_id`; revogar ou listar a sessão de outro dono é impossível por construção, não por verificação posterior (NFR-009).
- **Conteúdo não confiável:** nenhum — login não processa conteúdo externo.
- **Ameaças relevantes:**
  - Força bruta sobre TOTP → mitigado pelo *rate limiting* nativo do Fortify.
  - Reutilização de um código de recuperação → marcado como usado no momento da autenticação, nunca reutilizável.
  - *Session fixation*/*hijacking* → o identificador de sessão é regenerado no login; cookies `HttpOnly`, `Secure`, `SameSite=Lax`.
  - Phishing → mitigado pela preferência por passkey (WebAuthn liga a credencial à origem).
  - Modelo de ameaças completo (STRIDE, 11 ameaças) em [`docs/security/threat-model-identity-access.md`](../security/threat-model-identity-access.md), com as mitigações e os testes a criar na E4.5.
- **Gestão de credenciais (T-12, acrescentado na E4.6b) [C]:** registar ou apagar passkeys e ler ou trocar o segredo TOTP e os códigos de recuperação exige uma autenticação nos últimos 10 min (D-05), através do `password.confirm` nativo: o login conta como confirmação, porque não há password. Fora da janela → 423. Cada alteração fica auditada (`auth.credential.*`).
- **Segredos:** nenhum em código; a chave de cifra de sessão/cookie usa a `APP_KEY` já gerida pelo Laravel.

## 5. Observabilidade

- **Spans:** `http.server POST /auth/login`, `http.server DELETE /auth/sessions/{id}`, `http.server GET /auth/sessions`.
- **Métricas:** `kai_auth_attempts_total{method,outcome}` (`method`: `passkey`\|`totp`\|`recovery_code`; `outcome`: `success`\|`failure`) — nomeada, mas **ainda não exportada**: não há stack de métricas antes do M03 (`grafana/otel-lgtm`, `kai-observability`). Por agora, os logs estruturados (abaixo) cobrem a auditoria; a métrica propriamente dita fica para o M03.
- **Logs (sem dados sensíveis):** `actor_id` (quando conhecido), `method`, `outcome`, `trace_id`; nunca o código TOTP, a resposta WebAuthn, nem o código de recuperação.

## 6. Contratos

Sem contratos novos. Login e sessões são internos ao Core Platform, consumidos directamente pelo `apps/web` (React) por HTTPS — não atravessam a fronteira Laravel ↔ Python, por isso não entram em `packages/contracts` (ADR-0002 só cobre essa fronteira). As rotas ficam documentadas no próprio código Laravel.

## 7. Plano de testes

- **Correcção à E4.2:** ao contrário do que esta secção assumia, **`laravel/passkeys`/`laravel/fortify` não têm *helpers* de teste para simular a cerimónia WebAuthn** sem hardware — a verificação criptográfica real só é exercitável com um autenticador real ou um *Virtual Authenticator* ao nível do browser. AC-02a (login por passkey) fica, por isso, sem teste de integração nesta spec; só é coberta a nível E2E (E4.6).
- **Feito na E4.5 (integração, 23 testes PHPUnit, `tests/Feature/Auth/`):** AC-02b, AC-02c, AC-02d, AC-02e, AC-02f, AC-02g; e os negativos do modelo de ameaças (T-01, T-04, T-05, T-06, T-08, T-10). T-09 (CSRF) não é testado a este nível — o Laravel desactiva a validação de CSRF durante testes automáticos por desenho (`runningUnitTests()`); confirmado manualmente contra a stack real que um token CSRF inválido é mesmo rejeitado (419).
- **Unitários:** validação de TOTP; geração e consumo de códigos de recuperação (uso único); regra "sessão revogada rejeita pedidos" — cobertos pelos testes de integração acima, sem ficheiros unitários à parte.
- **E2E (feito, E4.6b, 2026-11-21) [C]:** `apps/web/e2e/ac-02-identity-access.spec.ts` (5 testes), corrido por `scripts/e2e.sh` numa stack descartável. AC-02a com o *Virtual Authenticator* do Chrome DevTools Protocol (registo da passkey pela UI → logout → login por passkey), AC-02b, AC-02c, AC-02e, AC-02f e AC-02g (login por código de recuperação) num browser real, mais T-02, T-03 e T-07. **Não cobertos no E2E** (ficam na integração, E4.5): AC-02d (campos da lista de sessões) e o uso único do código de recuperação da AC-02g. A auditoria de cada login, com o `method`, é confirmada no log real pelo script.
- **Bootstrap de credenciais (acrescentado na E4.6b) [C]:** o `kai:create-owner` cria o owner sem credencial nenhuma, e não havia como obter uma. Agora: `kai:enable-totp {email} {--force}` activa o TOTP pela CLI (operador de confiança; fica já confirmado), mostra o segredo e os códigos de recuperação **uma única vez** e recusa rodar um segredo activo sem `--force`. A passkey regista-se depois do primeiro login, na página de sessões. Testes: `tests/Feature/EnableTotpCommandTest.php`.
- Dados sintéticos; sem rede nem chaves reais.

## 8. Fora de âmbito

- RBAC completo (FR-046: o MVP só valida por ferramenta, não por papel).
- Registo público de utilizadores (D-05: só por CLI).
- **Exigência** de re-autenticação para operações de nível 5 — o campo `last_authenticated_at` entra agora (barato, evita uma migração depois), mas a verificação em middleware só chega com o M05 (quando os níveis ≥ 5 existirem de facto).
- Sessões de desktop/mobile (fase posterior, p.13).
- Login federado (Google, GitHub OAuth) — não pedido pelo PDF nem pelas decisões do owner.

## 9. Perguntas abertas

Nenhuma P-xxx nova. Uma decisão tomada directamente, sem abrir pergunta: o número e formato dos códigos de recuperação seguem o valor por omissão do `laravel/fortify` (8 códigos alfanuméricos de uso único) — **[H]**, ajustável sem mudança de arquitectura se o owner preferir outro valor.
