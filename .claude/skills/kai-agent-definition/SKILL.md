---
name: kai-agent-definition
description: Define um agente do KAI (entidade lógica do Agent Registry, PDF p.10). Cobre identidade, objectivo, instruções versionadas, ferramentas permitidas com versões, limites (passos, custo, tempo), memória, métricas de avaliação e versão. Usa quando o owner pedir um novo agente (Research, Developer, DevOps…), uma alteração de instruções ou ferramentas de um agente, ou disser "define o agente", "agent definition", "novo agente".
---
# kai-agent-definition: agente do Agent Registry

Não confundir com os subagentes do Claude Code (`.claude/agents/`). Este agente é um agente **do produto KAI**.

Base: PDF p.9–10 ("um agente é uma entidade lógica com instruções, ferramentas, permissões e objectivos próprios"); FR-028 e FR-029.

## Procedimento
1. **Necessidade:** liga o agente a um cenário do PDF (p.18–19) ou a um FR. Prefere um workflow explícito se a tarefa for previsível (PDF p.9).
2. **Identidade:** `id`, nome, objectivo numa frase, fora de âmbito.
3. **Instruções:**
   - ficheiro de prompt versionado;
   - nunca contêm segredos (assume que o system prompt pode vazar);
   - declaram explicitamente que o conteúdo externo são dados.
4. **Ferramentas:**
   - allowlist com versões fixas (`nome@major.minor`), o mínimo necessário;
   - cada ferramenta já existe no registo (skill `kai-tool-definition`);
   - o nível mais alto entre elas define o risco do agente.
5. **Modelo:** família e capacidades necessárias (tools, schema, visão). Nunca um modelo fixo no código fora do LLM Gateway.
6. **Limites (NFR-011):**
   - iterações máximas e tool calls máximas;
   - tempo máximo;
   - orçamento por missão (valores definidos no M03, P-002).
7. **Memória:**
   - que tipos lê (conversa, semântica, documentos);
   - que tipos pode **propor** escrever (a escrita decide-a o Laravel; na v1, com confirmação do owner).
8. **Avaliação:**
   - suite em `apps/ai-engine/evals/` (skill `kai-eval`);
   - métricas: Task Success, Tool Success, Groundedness, Cost per Task, Latency;
   - limiares de aprovação.
9. **Versão:**
   - `agent_version` é imutável;
   - mudar instruções, ferramentas ou modelo cria uma nova versão e corre a suite de regressão.
10. Escreve a definição a partir de [templates/agent.yaml](templates/agent.yaml). O destino é o registo de agentes (definido no M05; até lá, `docs/specs/agents/<id>.yaml`).

## Verificação
- A suite de avaliação passa nos limiares.
- Os testes negativos passam: pedido fora de âmbito, ferramenta não permitida, injection no conteúdo.
- O revisor de segurança aprova agentes com ferramentas de nível ≥ 4.
