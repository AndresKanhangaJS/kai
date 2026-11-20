# Identidade visual mínima (M01)

- **Estado:** Rascunho
- **Data:** 2026-11-20
- **Âmbito:** o mínimo para o MVP (`docs/specs/001-mvp-fatia-vertical.md`) — um ponto de partida para a UI React, não um sistema de design completo.
- **Fontes:** [C p.12] interface e experiência; [H] capa do PDF (p.1, elementos gráficos não confirmados, `kai-vision.md` TODO); stack de UI (`analysis.md` §6, `kai-vision.md` §09): React, TypeScript, Vite, Tailwind CSS, shadcn/ui.

## 1. Princípio

**Dark-first, minimalista e acessível (FR-066).** O KAI nunca obriga a um tema claro na v1; a legibilidade e o contraste são verificados contra o fundo escuro, não o inverso. A estética visual do próprio documento de produto (fundo quase-preto, acentos em ciano, tipografia técnica) é o ponto de partida [H], por ser a única referência visual que o owner já produziu.

## 2. Paleta

**[H]**, ponto de partida — a verificar com uma ferramenta real de contraste (ex. `axe`, Chrome DevTools) antes de entrar em código, não só por inspecção.

| Papel | Cor | Uso |
|---|---|---|
| Fundo base | `#0B0F17` (quase-preto, tom azulado) | Fundo da aplicação |
| Texto principal | `#E6EAF2` | Texto sobre o fundo base (contraste alvo ≥ 4.5:1, NFR-030) |
| Acento primário | `#22D3EE` (ciano) | Marca, botões primários, estado Idle/Processing |
| Superfície | `#121826` | Painéis, cartões, barras |
| Borda/separador | `#2A3344` | Divisórias, *outlines* |

A paleta não define cores por módulo (Core Platform vs AI Engine no PDF usam ciano vs magenta): isso é um diagrama de arquitectura, não um padrão de UI, e não se transporta para a interface.

## 3. Tipografia mínima

- **UI e texto corrido:** uma sans-serif legível e já compatível com shadcn/ui (ex. Inter), sem licença a validar — é tipografia de sistema/aberta.
- **Código, logs, IDs técnicos (trace_id, hash):** uma monoespaçada aberta (ex. JetBrains Mono), para reforçar o lado "laboratório de engenharia" (`kai-vision.md` §00) sem exigir uma fonte paga.
- Sem itálico nem pesos decorativos no MVP; só regular e semibold.

## 4. Estados visuais do núcleo — subconjunto do MVP (FR-068)

**[C p.12, subconjunto `analysis.md` FR-068]** O PDF define 7 estados; o MVP entra com 5, sem `Listening` nem `Speaking` (não há voz antes do M06). Cada estado leva sempre texto ou ícone, nunca só cor (WCAG 2.2 AA — a cor sozinha não pode ser o único sinal).

| Estado | Cor | Reforço não-cor | Quando aparece |
|---|---|---|---|
| Idle | Acento primário (ciano), opacidade reduzida | Ícone de círculo parado | À espera de interacção |
| Processing | Acento primário (ciano), pulsação | Ícone de três pontos animado | A interpretar o pedido (etapas 2–3 do ciclo) |
| Executing | Âmbar `#F5A623` | Ícone de engrenagem/play | A correr uma ferramenta (`github.repo.read`, `notes.save`) |
| Awaiting approval | Violeta `#A78BFA` | Ícone de mão/pausa | Missão em `AWAITING_APPROVAL` (ADR-0013) |
| Error | Vermelho `#F87171` | Ícone de alerta + motivo em texto | Missão em `FAILED`/`CANCELLED` com motivo (AC-09) |

No MVP isto é um **badge de estado simples (FR-007)**, não o núcleo visual animado do PDF — esse fica para depois.

## 5. Fora de âmbito

- Núcleo visual 3D / animado (Three.js, React Three Fiber) — FR-007 fica um badge no MVP.
- Estados `Listening` e `Speaking` — chegam com a voz, M06.
- Tema claro.
- Qualquer variação de marca por módulo ou por agente.

## 6. Ligações

- Usado por: `docs/product/prd.md` §8; `docs/milestones/M01-product-discovery.md`, Épico E5.
- Precede a implementação da Web (`apps/web`, M02) — esta identidade ainda não foi validada em componentes reais nem testada para contraste com ferramentas automáticas.
