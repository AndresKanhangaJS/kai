## O quê e porquê
<!-- Resumo em 1–3 frases. Liga a spec, os FR/NFR e os ADRs. -->

- **Spec / requisitos:**
- **ADRs:**

## Como foi verificado
<!-- Comandos executados e resultado (cola o output relevante). -->

## Segurança
- [ ] Níveis de operação e aprovações correctos (ADR-0004); autorização fora do LLM
- [ ] `user_id` aplicado em todos os acessos a dados próprios
- [ ] Conteúdo externo tratado como não confiável
- [ ] Sem segredos nem dados pessoais (código, fixtures, logs, prompts)
- [ ] Sem dependências novas, ou dependências aprovadas e com licença verificada

## Contratos e observabilidade
- [ ] Contratos alterados antes do código, com compatibilidade classificada (`kai-contract`)
- [ ] Spans, métricas e logs segundo `.claude/rules/observability.md`

## Definition of Done
- [ ] O requisito está documentado e tem critérios de aceitação
- [ ] A implementação respeita os limites de domínio e os contratos
- [ ] Existem testes adequados e passam localmente
- [ ] Logs e erros são tratados sem expor dados sensíveis
- [ ] A documentação foi actualizada
- [ ] A alteração foi revista antes de integrar
