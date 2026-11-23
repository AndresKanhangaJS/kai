---
name: kai-threat-model
description: Produz um modelo de ameaças para uma funcionalidade, ferramenta, agente ou fluxo do KAI, combinando STRIDE e OWASP Top 10 para LLM (numeração 2025, verificada). Cobre prompt injection directa e indirecta, abuso de ferramentas, exfiltração, envenenamento de memória ou RAG, SSRF e privilégio excessivo. Usa quando houver uma ferramenta de nível ≥ 4, acesso a rede, conteúdo externo, novos dados pessoais, autenticação, ou quando o owner disser "modelo de ameaças", "threat model", "isto é seguro?", "STRIDE".
---
# kai-threat-model: STRIDE + OWASP LLM

Referências:
- ADR-0004 (o LLM não é fronteira de segurança).
- `.claude/rules/security.md`.
- OWASP Top 10 for LLM Applications **2025**: os IDs abaixo seguem esta lista, verificada a 2026-11-20 em genai.owasp.org/llm-top-10/.
- A edição 2026 existe (publicada em Agosto de 2026, genai.owasp.org/resource/owasp-genai-llm-top-10-2026/), mas a lista dela **ainda não foi verificada** [P]. Até lá, usa os IDs 2025 com o sufixo `:2025` (A-26).
- OWASP Top 10 for Agentic Applications (iniciativa ASI do OWASP GenAI): a edição e os IDs estão por verificar [P].

## Procedimento
1. **Âmbito:** o que entra (componentes, fluxos, dados, ferramentas) e o que fica de fora.
2. **Diagrama de fluxo de dados** em Mermaid (`flowchart`), com as **fronteiras de confiança** marcadas:
   - browser ↔ Laravel;
   - Laravel ↔ RabbitMQ ↔ Python;
   - Python ↔ fornecedor LLM;
   - Python ↔ serviços externos;
   - conteúdo externo → contexto do LLM.
3. **Activos:**
   - credenciais;
   - dados do owner (conversas, documentos, memória);
   - permissões e grants;
   - orçamento LLM;
   - integridade da auditoria.
4. **Enumeração:** para cada elemento e fluxo, aplica STRIDE e a checklist LLM abaixo. Preenche [templates/threat-model.md](templates/threat-model.md).
5. **Avaliação:** probabilidade e impacto (A/M/B). Indica onde a mitigação é aplicada (contexto e componente) e como se verifica (teste, regra, gate).
6. **Mitigações:**
   - preferir controlos determinísticos fora do LLM;
   - "pedir ao modelo para não fazer" **não** conta como mitigação.
7. **Risco residual:** o que fica, e se precisa de decisão do owner (P-xxx).
8. **Testes:** cada mitigação crítica vira um teste negativo (ver `.claude/rules/testing.md`).
9. Guarda em `docs/security/threat-model-<tema>.md`, ou anexa à spec, e liga a partir da spec ou do ADR.

## Checklist LLM / agentes (obrigatória)
| ID | Ameaça | Perguntas |
|---|---|---|
Cada linha da checklist tem de aparecer no documento, seja como ameaça, seja como "não aplicável" com justificação.

| ID (2025) | Ameaça | Perguntas |
|---|---|---|
| LLM01 | Prompt Injection (directa/indirecta) | Que conteúdo externo entra no contexto? Está delimitado e marcado? A missão fica *tainted*? |
| LLM02 | Sensitive Information Disclosure | Chegam segredos ou PII ao prompt, ao fornecedor, aos logs, aos traces? |
| LLM03 | Supply Chain | Dependências, modelos e servidores MCP fixados e revistos? |
| LLM04 | Data and Model Poisoning | Pode conteúdo externo entrar na memória longa ou no índice sem confirmação? |
| LLM05 | Improper Output Handling | O output do LLM é renderizado ou executado sem sanitização? Imagens ou links remotos? |
| LLM06 | Excessive Agency | As ferramentas são estreitas? O nível é fixo? Há grant de uso único? E aprovação? |
| LLM07 | System Prompt Leakage | O system prompt tem algo que não possa vazar? |
| LLM08 | Vector and Embedding Weaknesses | O filtro `user_id` é imposto pelo código? Há re-verificação no MySQL? |
| LLM09 | Misinformation | Há citações obrigatórias? Groundedness avaliada? |
| LLM10 | Unbounded Consumption | Há tectos de tokens, custo, passos e tempo? Detecção de loops? Kill switch? |
| SSRF | Fetch para a rede interna | Há allowlist? Bloqueio de IPs privados após DNS e redirects? |
| EXFIL | Exfiltração por ferramentas | Uma escrita externa depois de ler dados privados exige aprovação? |

## Saída
- O documento do modelo de ameaças.
- Uma lista curta das mitigações a implementar, com os testes correspondentes.
- Os riscos residuais que pedem decisão do owner.
