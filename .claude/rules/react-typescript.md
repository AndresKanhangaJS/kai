---
paths:
  - "apps/web/**"
---
# Web (`apps/web`): React + TypeScript + Vite

## Código
- TypeScript `strict`; sem `any` implícito; tipos de API gerados a partir do OpenAPI, nunca escritos à mão.
- Componentes pequenos, sem lógica de negócio. A autorização decide-se no servidor; a UI só a reflecte.
- Estado do servidor separado do estado da UI. Streaming de tokens via Reverb, reconciliado com a mensagem final (ADR-0009).

## Segurança no cliente
- Renderiza o output do LLM como texto ou markdown sanitizado; nunca uses `dangerouslySetInnerHTML` com conteúdo do modelo.
- Não carregues imagens remotas automaticamente (CSP `img-src 'self'`); mostra os links com o URL completo.
- O ecrã de aprovação mostra a ferramenta, o nível e os argumentos reais (do servidor), não o resumo do LLM.
- Não guardes tokens em `localStorage`; a sessão vive em cookie `HttpOnly` gerido pelo Laravel.

## UX
- Dark-first, minimalista, WCAG 2.2 AA: navegável por teclado, foco visível, contraste verificado.
- Os estados do núcleo (Idle, Processing, Executing, Awaiting approval, Error) são explícitos e acessíveis (`aria-live`).
- Os erros mostram um motivo compreensível e o `trace_id`; nunca stack traces.

## Testes
- Vitest e Testing Library para componentes; Playwright para E2E (AC-03, AC-05, AC-09).
- Comandos: `scripts/ci/web.sh` (`tsc -b`, `oxlint`, Vitest) e `scripts/e2e.sh` (Playwright). Lint: `oxlint`, não ESLint (ADR-0014). Ver `docs/engineering/ci.md`.
