---
name: kai-tool-definition
description: Define uma ferramenta do Tool Registry do KAI. A definição inclui nome e versão, JSON Schema de entrada e saída, modo (read-only, draft ou write), nível de operação 1–6, permissões, política de aprovação, timeout, retry, limites, auditoria e testes. Usa quando for preciso criar, versionar ou rever uma ferramenta que um agente possa chamar, ou quando o owner disser "nova ferramenta", "tool", "conector", "o agente precisa de…", "define the tool".
---
# kai-tool-definition: ferramenta do Tool Registry

Base: PDF p.10 (Tool Registry), p.13 (níveis 1–6); ADR-0004; `docs/product/analysis.md` §5.4.

## Procedimento
1. **Justificação:** liga a ferramenta a um FR e a um critério de aceitação. Uma ferramenta sem caso de uso não entra.
2. **Desenho estreito:**
   - uma operação por ferramenta, com argumentos tipados;
   - nada de "executa comando", "query SQL livre" ou "fetch qualquer URL";
   - prefere vários read-only a um write genérico.
3. **Classificação:**
   - **Modo:** `read-only` | `draft` | `write`.
   - **Nível:** 1–6, fixo, segundo a tabela da análise §5.4. Na dúvida, usa o nível mais alto.
   - O nível 6 nunca é registado. Se a ferramenta só faz sentido como nível 6, a resposta é não.
4. **Schemas:**
   - JSON Schema de entrada e de saída, com `additionalProperties: false`;
   - limites de tamanho (`maxLength`, `maxItems`) e `enum` onde possível;
   - IDs validados quanto ao dono (`user_id`) no executor, não no schema.
5. **Política:**
   - aprovação (nenhuma / por política / sempre + re-autenticação);
   - regra de *taint*: depois de ler conteúdo externo, o nível 4 exige aprovação.
6. **Limites:**
   - timeout em segundos;
   - retry só para erros transitórios e só se a operação for idempotente;
   - tamanho máximo da resposta;
   - rate limit.
7. **Credenciais:**
   - nunca no contexto do LLM;
   - libertadas pelo Laravel, ligadas a um grant (P-007);
   - escopo mínimo (read-only por omissão).
8. **Egress:** se a ferramenta faz rede, lista os domínios permitidos e aplica o bloqueio de IPs privados (NFR-014).
9. **Output:**
   - é dado não confiável;
   - corre um scan de segredos antes de o devolver ao LLM;
   - trunca com um marcador explícito.
10. **Auditoria:** confirma que a execução gera o registo do NFR-002.
11. **Ameaças:** para ferramentas de nível ≥ 4 ou com acesso à rede, corre a skill `kai-threat-model`.
12. **Testes:**
    - caso feliz;
    - schema inválido;
    - sem grant;
    - grant expirado;
    - args alterados depois da aprovação;
    - `user_id` de outro dono;
    - output com injection ("ignore previous instructions").
13. Escreve a definição a partir de [templates/tool.yaml](templates/tool.yaml). O destino é o registo de ferramentas (local definido no M05; até lá, `docs/specs/tools/<nome>.yaml`).

## Versionamento
- `nome@major.minor`. Mudar os schemas de forma incompatível ou subir o nível cria uma nova major.
- Cada `agent_version` fixa versões de ferramentas.
