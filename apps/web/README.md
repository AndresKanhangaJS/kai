# `apps/web`: Command Center do KAI

React + TypeScript + Vite. Dark-first ([identidade visual](../../docs/product/identidade-visual.md)), WCAG 2.2 AA (NFR-030).

## Ecrãs

- **Login** (SPEC-002): TOTP, código de recuperação ou passkey.
- **Conversa** (página inicial depois do login): protótipo com respostas simuladas ([SPEC-005](../../docs/specs/005-prototipo-chat.md)), descrito abaixo.
- **Sessões** (SPEC-002): lista e revogação de sessões e registo de passkey.

## Protótipo do chat (SPEC-005)

As respostas são geradas no browser por `src/chat/simulated.ts`. Nada vai para o servidor e nada fica guardado: recarregar a página apaga a conversa. O aviso "Respostas simuladas" está sempre visível e tem um selector de cenário: resposta normal, tempo esgotado a meio, orçamento excedido e fornecedor indisponível.

- **`transport.ts`:** interface `ConversationTransport` com os eventos na forma dos contratos v1 (deltas com `seq`, `completed` com `delta_count`, `failed` com motivo, erro seguro e `trace_id`). **[P]** O transporte real (E5.1: API do Laravel e Reverb) implementa a mesma interface e substitui o simulado.
- **`reconcile.ts`:** monta a resposta por `seq`; deltas trocados ou repetidos não estragam o texto (prepara a AC-004-10). O simulador troca e repete deltas de propósito.
- **Robustez (revisão de segurança):**
  - cada turno tem um token, e os eventos atrasados, repetidos ou de outro turno são ignorados;
  - os motivos e os erros são validados em runtime (`reasonLabel`), por isso um motivo desconhecido ou `__proto__` não derruba o ecrã;
  - há tectos para os `seq` (65 536) e para a resposta (100 000 caracteres);
  - uma resposta com buracos fica marcada como incompleta;
  - uma `ErrorBoundary` mantém a navegação viva se o ecrã falhar.
- **Segurança:** a resposta é sempre mostrada como texto literal (`white-space: pre-wrap`), nunca como HTML nem markdown. Nenhuma imagem nem link é criado a partir dela (AC-005-06).
- **Acessibilidade:**
  - o badge de estado mostra sempre texto e ícone;
  - o fim da resposta e os erros são anunciados uma vez (`aria-live`);
  - o foco volta ao compositor;
  - o histórico é alcançável por teclado;
  - as animações desligam-se com `prefers-reduced-motion`;
  - o `axe-core` corre no Vitest (estrutura) e no E2E (com contraste).

### Ver no browser

1. Com a stack de dev a correr, abre <http://localhost:5173>.
2. Entra com o owner. A BD de dev foi recriada vazia a 2026-11-23, por isso antes é preciso criar o owner e activar o TOTP com `kai:create-owner` e `kai:enable-totp` (ver `apps/api`).

## Qualidade

```bash
scripts/ci/web.sh   # tsc -b, oxlint e Vitest
scripts/e2e.sh      # Playwright numa stack descartável (a stack de dev tem de estar parada)
```

Dependências novas pedem a aprovação do owner. O `axe-core` 4.14.0 (MPL-2.0) é só de desenvolvimento e foi aprovado na P-023.
