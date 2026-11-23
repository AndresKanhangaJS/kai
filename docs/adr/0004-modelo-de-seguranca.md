# ADR-0004: Modelo de segurança: o LLM não é fronteira; níveis 1–6

- **Estado:** Substituído por ADR-0013
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.9, p.10, p.13–14; ADR-0002, 0010; `docs/product/analysis.md` §5.1, §5.3, §5.4; P-003, P-004 (fechadas por este ADR); P-005 (lista do nível 6, ainda aberta)

## Contexto
- Os agentes do KAI lêem conteúdo não confiável [C p.14] e chamam ferramentas que alteram dados [C p.10].
- O LLM pode ser manipulado por prompt injection e alucinar argumentos.
- O PDF afirma que o modelo não é uma fronteira de segurança [C p.13] e que a validação de permissões fica fora do LLM [C p.9].
- O PDF não diz onde fica essa validação (A-04), nem como os modos de ferramenta se relacionam com os níveis (A-06), nem as transições da missão: mostra 5 estados no diagrama e 8 na tabela, sem definir transições (A-05).

## Opções consideradas
1. **PDP determinístico no Laravel; enforcement no Laravel e no Python através de *execution grants*.**
2. Instruções ao LLM para se auto-policiar. Rejeitada pela p.13.
3. PDP no Python. O componente mais exposto a injection autorizar-se-ia a si próprio.
4. Todas as ferramentas executadas no Laravel. Contraria o Tool Execution em Python (p.8).
5. **Máquina de estados da missão com 8 estados e transições explícitas** (`analysis.md` §5.3), versus manter só os 5 estados do diagrama da p.9 — rejeitada por não distinguir `AWAITING_APPROVAL` de `PAUSED`, nem o motivo de uma falha.

## Decisão
- **Opção 1**, para a validação de permissões.
- **PEP-1, no gateway Laravel:** identidade, sessão e dono do recurso.
- **PEP-2, no Tool Execution (Python):** verifica um JWS assinado pelo Laravel (só tem a chave pública). Validade ≤ 60 s, `jti` de uso único, ligado a missão, passo, ferramenta@versão, hash dos argumentos, modo, nível e dono.
- Cada operação de ferramenta tem um nível fixo no Tool Registry; o LLM nunca o escolhe.

**Níveis, modo e aprovação (P-004):**

| Nível | Modo | Aprovação |
|---|---|---|
| 1 Consulta | read-only | Nenhuma; só verificação de acesso |
| 2 Análise | read-only | Nenhuma, dentro do âmbito autorizado |
| 3 Rascunho | draft | Nenhuma; nunca envia nem publica |
| 4 Alteração | write | Por política: automática se interna e reversível; exige aprovação se externa, irreversível, ou a missão estiver *tainted* |
| 5 Sensível | write | Sempre explícita, com re-autenticação nos últimos 10 min, e auditoria |
| 6 Proibida | — | Nunca registada nem exposta ao LLM; sempre recusada (lista exacta em P-005, ainda aberta) |

**Máquina de estados da missão (P-003):**
- `PENDING → PLANNING → RUNNING`
- `RUNNING ⇄ AWAITING_APPROVAL`
- `RUNNING ⇄ PAUSED`
- `RUNNING → COMPLETED | FAILED`
- De qualquer estado não terminal `→ CANCELLED`
- Aprovação rejeitada `→ CANCELLED`; aprovação expirada `→ FAILED` (motivo `approval_timeout`)
- Grafia canónica: `AWAITING_APPROVAL`

Cada decisão de nível/aprovação e cada transição de missão são auditadas (NFR-002).

## Consequências
- **Positivas:** autorização testável e determinística; injection não chega a operações sem aprovação; a máquina de estados remove a ambiguidade entre "à espera de aprovação" e "pausada".
- **Negativas:** uma ida e volta extra por ferramenta; os metadados do Tool Registry e o estado da missão tornam-se críticos para a segurança; `PAUSED` fica definido mas fora do subconjunto do MVP (FR-061).

## Verificação
- Teste de arquitectura: não há caminho até um adaptador sem grant (NFR-001).
- Teste da máquina de estados: todas as transições listadas passam; as não listadas são rejeitadas.
- Suite negativa: nível 6, grant expirado, argumentos alterados, aprovação expirada.
- Suite de injection na CI (NFR-005).
