# SPEC-<NNN>: <título>

- **Estado:** Rascunho | Aprovada | Implementada | Obsoleta
- **Data:** AAAA-MM-DD
- **Milestone:** M<NN>
- **Autor:** <nome>
- **Requisitos:** FR-xxx, NFR-xxx (ver `docs/product/analysis.md`)
- **ADRs relacionados:** ADR-NNNN

## 1. Contexto
<Problema e motivação. Origem: PDF p.N / decisão D-xx. Etiquetas [C]/[H]/[P].>

## 2. Objectivo
<Uma ou duas frases sobre o resultado para o utilizador.>

## 3. Critérios de aceitação
| ID | Dado | Quando | Então | Tipo de teste |
|---|---|---|---|---|
| AC-<NNN>-01 | | | | unit / integração / contrato / E2E / eval |
| AC-<NNN>-02 (negativo) | | | | |

## 4. Segurança e privacidade
- **Níveis de operação:** <acção → nível 1–6 → política de aprovação>
- **Dados tocados e isolamento:** <tabelas/colecções; filtro `user_id`>
- **Conteúdo não confiável:** <fontes; regra de *taint*>
- **Ameaças relevantes:** <resumo; link para o threat model, se existir>
- **Segredos:** <nenhum / onde vivem (variáveis de ambiente)>

## 5. Observabilidade
- **Spans:**
- **Métricas:**
- **Logs (sem dados sensíveis):**

## 6. Contratos
<OpenAPI/AsyncAPI afectados; versão; compatibilidade.>

## 7. Plano de testes
<Pirâmide: o que se testa em cada nível; fixtures sintéticas; LLM fake.>

## 8. Fora de âmbito
-

## 9. Perguntas abertas
| ID | Pergunta | Recomendação | Bloqueia? |
|---|---|---|---|
| P-xxx | | | sim/não |
