# SPEC-005: Protótipo visual do chat no Command Center

- **Estado:** Aprovada (owner, 2026-11-24)
- **Data:** 2026-11-24
- **Milestone:** M03 (antecipa o E5, em paralelo com o E4; decisão do owner, 2026-11-24)
- **Autor:** Claude Code, para o owner
- **Requisitos:** FR-001, FR-007 (badge no MVP), FR-008, FR-066, FR-068 (subconjunto), NFR-030; prepara AC-03 e AC-09 (ver `docs/product/analysis.md`)
- **ADRs relacionados:** ADR-0015 (streaming pelo Reverb), ADR-0002 (o Laravel decide e persiste)

## 1. Contexto
- **[C]** O owner pediu os primeiros ensaios visuais e escolheu (2026-11-24) fazer um protótipo do chat já, com respostas simuladas no browser, e seguir com o E4 (Conversations no Laravel) em paralelo.
- **[C]** Hoje a web tem só o login e a lista de sessões (M02 E4). A conversa real precisa do E4 (mensagens, outbox, eventos) e da E3.4b (deltas no Reverb), que ainda não existem.
- **[C]** Os eventos que a UI vai receber já estão nos contratos v1 (SPEC-003, SPEC-004): deltas com `seq`, `turn.completed` com `delta_count`, `turn.failed` com `reason` e um `error` seguro (`code`, `message` ≤ 500, `retryable`).
- **[H]** Um transporte simulado com a mesma forma desses eventos permite afinar o ecrã agora e trocá-lo pelo real (E5.1) sem reescrever a vista. O protótipo serve também de entrada para a spec de Conversations (E4.1).

## 2. Objectivo
O owner, autenticado, abre o ecrã de conversa, escreve uma mensagem e vê a resposta a chegar token a token. Vê também os estados Idle, Processing e Error (com o motivo) e pode cancelar. Tudo com respostas simuladas e assinaladas como tal.

## 3. Critérios de aceitação
| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-005-01 | O owner autenticado | Abre a aplicação | Vê o ecrã de conversa como página inicial, com o aviso visível "Respostas simuladas" e o badge de estado em Idle (texto e ícone, não só cor); as sessões continuam acessíveis pela navegação | unit, E2E |
| AC-005-02 | O ecrã de conversa em Idle | O owner envia uma mensagem (botão ou Enter; Shift+Enter muda de linha) | A mensagem aparece logo na conversa, o badge passa a Processing e a resposta simulada aparece incrementalmente, delta a delta, até ficar completa; o badge volta a Idle | unit, E2E |
| AC-005-03 | Uma resposta em curso | Chegam deltas fora de ordem ou repetidos (por `seq`) e o fim indica `delta_count` | A resposta final mostrada é a do texto completo, sem duplicados nem buracos (reconciliação, prepara a AC-004-10) | unit |
| AC-005-04 | Uma resposta em curso | O owner carrega em Cancelar | A geração pára em menos de 2 s, o texto parcial fica marcado como interrompido e o badge mostra Error com o motivo "cancelado" (prepara a AC-09) | unit, E2E |
| AC-005-05 | O cenário simulado de falha (`timeout`, `budget_exceeded`, `provider_unavailable`) | O owner envia uma mensagem | O badge mostra Error com o motivo em português, a mensagem segura e o `trace_id` em monoespaçada; o owner pode enviar outra mensagem a seguir | unit |
| AC-005-06 (negativo) | Uma resposta simulada com `<img src=x onerror=…>`, `<script>`, um link e markdown | É mostrada | Aparece como texto literal: nenhum elemento HTML, imagem ou link é criado a partir do conteúdo (regra `security.md`: nada de imagens remotas nem links seguidos a partir de output do LLM) | unit |
| AC-005-07 (negativo) | Uma mensagem vazia, só com espaços ou acima de 32 000 caracteres | O owner tenta enviar | O envio é recusado na UI com uma mensagem clara; nada é enviado ao transporte | unit |
| AC-005-08 | O owner a usar só o teclado ou um leitor de ecrã | Envia e recebe uma resposta | Todos os controlos têm nome acessível e foco visível; o fim da resposta e os erros são anunciados uma vez por região `aria-live` (não cada token); as animações respeitam `prefers-reduced-motion`; sem violações axe sérias | unit (axe), E2E |
| AC-005-09 (negativo) | Um utilizador sem sessão | Abre a aplicação | Vê o login, não o chat: o protótipo não abre nenhum caminho sem autenticação | unit, E2E |

## 4. Segurança e privacidade
- **Níveis de operação:** enviar uma mensagem simulada → nível 1 (só leitura e conversa local); nenhuma ferramenta.
- **Dados tocados e isolamento:** nenhum dado persistido nem enviado ao servidor; a conversa vive só em memória no browser e desaparece ao recarregar. Sem `localStorage`.
- **Conteúdo não confiável:** a resposta (hoje simulada, amanhã do LLM) é tratada como não confiável: mostrada como texto, sem HTML nem markdown renderizado (AC-005-06).
- **Ameaças relevantes:** XSS a partir da resposta (mitigado pela AC-005-06); confundir o owner com respostas falsas (mitigado pelo aviso permanente da AC-005-01); um atalho de desenvolvimento que salte o login (proibido, AC-005-09).
- **Segredos:** nenhum.

## 5. Observabilidade
- **Spans / métricas:** nenhum (só browser; a instrumentação da web fica para o E7).
- **Logs:** nenhum novo; o `trace_id` simulado só aparece no ecrã, como o real aparecerá (FR-068, AC-09).

## 6. Contratos
Nenhum alterado. O transporte simulado imita a forma dos eventos v1 (`seq`, `delta_count`, `reason`, `error`) sem os importar como dependência; a ligação real ao canal privado do Reverb é decidida no E4.6/E3.4b.

## 7. Plano de testes
- **Unitários (Vitest + Testing Library):** o simulador com tempo controlado; a reconciliação por `seq`; os estados do badge; cancelar; cada cenário de falha; o texto literal (AC-005-06); validação do envio; a regressão do login.
- **Acessibilidade:** verificação axe nos testes de componente **se** o owner aprovar a dependência (P-023); senão, verificação manual com o Lighthouse/axe do Chrome registada na entrega.
- **E2E (Playwright):** login, enviar, ver a resposta completa e cancelar, no `scripts/e2e.sh` existente.
- **Visual:** o owner vê o ecrã no Chrome; capturas de ecrã na entrega.

## 8. Fora de âmbito
- Persistência, histórico de conversas e lista de conversas (FR-002, E4).
- Ligação ao Laravel, ao RabbitMQ, ao Reverb ou ao AI Engine.
- Tailwind CSS e shadcn/ui (citados na identidade visual): seriam dependências novas e uma decisão à parte; o protótipo usa o CSS existente.
- Núcleo visual animado (FR-007 completo), voz, tema claro, estados Executing e Awaiting approval (sem ferramentas no M03).
- Markdown e blocos de código formatados nas respostas (exigem uma decisão de sanitização).

## 9. Perguntas abertas
| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-023 | Adoptar `axe-core` como dependência de dev para testar a AC-005-08? | **Fechada (owner, 2026-11-24):** sim, só em dev. `axe-core` 4.14.0 (publicada a 2026-10-05; a 4.14.1 tem menos de 14 dias), MPL-2.0, sem dependências (npm, verificado a 2026-11-24). A MPL-2.0 é copyleft por ficheiro e o pacote só corre nos testes, não é distribuído com a web | Não |
| P-024 | Como escolhe o owner o cenário simulado (normal ou falhas)? | **Fechada (owner, 2026-11-24):** um selector discreto dentro do aviso "Respostas simuladas", que sai com o transporte real | Não |
