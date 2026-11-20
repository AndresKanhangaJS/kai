---
name: kai-review
description: Faz uma revisão multi-lente do diff actual ou de um PR do KAI, olhando a correcção, segurança, testes, contratos, observabilidade e Definition of Done, com saída estruturada por severidade. Usa depois de implementar e antes de propor um commit ou PR, ou quando o owner disser "revê", "review", "está pronto para merge?", "analisa este diff".
---
# kai-review: revisão multi-lente

## Entradas
- O diff: `git diff` (não staged), `git diff --staged`, ou o intervalo indicado (`git diff main...HEAD`).
- A spec, os ADRs e os critérios de aceitação ligados à alteração.

## Lentes (aplica todas; para cada uma, lê o código real, não só o diff)
1. **Correcção:** a lógica cumpre os critérios de aceitação? Casos limite, erros, concorrência, idempotência, transacções.
2. **Segurança** (`.claude/rules/security.md`):
   - autorização fora do LLM;
   - grants;
   - nível de operação;
   - `user_id` em todas as queries;
   - conteúdo não confiável;
   - segredos;
   - injection: SQL, prompt, XSS no output do LLM;
   - SSRF.
   Para alterações sensíveis, delega também no subagente `kai-security-reviewer`.
3. **Testes:**
   - cada critério tem teste;
   - há casos negativos de segurança;
   - não há rede nem chaves reais;
   - nenhum teste foi enfraquecido.
4. **Contratos:** mudanças de payload ou endpoint passaram pela skill `kai-contract`? Classificação de compatibilidade correcta?
5. **Observabilidade:** spans, métricas e logs com os nomes da regra; `traceparent` propagado; nada sensível nos logs.
6. **Arquitectura:**
   - limites de módulo e bounded context respeitados;
   - nenhuma escrita do Python em tabelas do Laravel;
   - nenhuma dependência nova sem aprovação.
7. **DoD:** os 6 pontos da Definition of Done (`CLAUDE.md`).

## Severidade
- **BLOQUEANTE:** viola segurança, contrato, um ADR aceite, perde dados, ou falha um critério de aceitação.
- **IMPORTANTE:** bug provável, teste em falta para um caminho relevante, observabilidade em falta.
- **MENOR:** legibilidade, nomes, duplicação.
- **NOTA:** sugestão opcional.

## Formato de saída
```
REVISÃO: <âmbito do diff>, <data>
Veredicto: APROVAR | APROVAR COM ALTERAÇÕES | REJEITAR

| # | Severidade | Lente | Ficheiro:linha | Problema | Evidência | Correcção sugerida |
|---|------------|-------|----------------|----------|-----------|--------------------|

DoD: [x]/[ ] por ponto, com justificação curta
Não verificado: <o que não foi possível confirmar e porquê>
```

## Regras
- Cada problema tem evidência: uma linha de código, o output de um comando, ou a ausência demonstrada de um teste.
- Se não houver problemas numa lente, escreve "sem observações" em vez de inventar.
- Não alteres código durante a revisão; propõe as correcções.
