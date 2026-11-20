# ADR-0004: Modelo de segurança: o LLM não é fronteira; níveis 1–6

- **Estado:** Proposto
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.9, p.10, p.13–14; ADR-0002, 0010; `docs/product/analysis.md` §5.1, §5.4; P-004, P-005

## Contexto
- Os agentes do KAI lêem conteúdo não confiável [C p.14] e chamam ferramentas que alteram dados [C p.10].
- O LLM pode ser manipulado por prompt injection e alucinar argumentos.
- O PDF afirma que o modelo não é uma fronteira de segurança [C p.13] e que a validação de permissões fica fora do LLM [C p.9].
- O PDF não diz onde fica essa validação (A-04), nem como os modos de ferramenta se relacionam com os níveis (A-06).

## Opções consideradas
1. **PDP determinístico no Laravel; enforcement no Laravel e no Python através de *execution grants*.**
2. **Instruções ao LLM para se auto-policiar.** Rejeitada pela p.13.
3. **PDP no Python.** O componente mais exposto a injection autorizar-se-ia a si próprio.
4. **Todas as ferramentas executadas no Laravel.** Contraria o Tool Execution em Python (p.8).

## Decisão
- **Opção 1.**
- **PEP-1, no gateway Laravel:** identidade, sessão e dono do recurso.
- **PEP-2, no Tool Execution (Python):** verifica um JWS assinado pelo Laravel (só tem a chave pública).
  - Validade ≤ 60 s, `jti` de uso único.
  - Ligado a missão, passo, ferramenta@versão, hash dos argumentos, modo, nível e dono.
- Cada operação de ferramenta tem um nível fixo no Tool Registry; o LLM nunca o escolhe.
- **Níveis:**
  - 1–3 sem aprovação;
  - 4 por política, com escalada obrigatória quando a missão está *tainted* (leu conteúdo externo);
  - 5 com aprovação explícita mais re-autenticação;
  - 6 nunca registado nem exposto.
- Cada decisão é auditada (NFR-002).

## Consequências
- **Positivas:** autorização testável e determinística; injection não chega a operações sem aprovação.
- **Negativas:** uma ida e volta extra por ferramenta; os metadados do Tool Registry tornam-se críticos para a segurança.

## Verificação
- Teste de arquitectura: não há caminho até um adaptador sem grant (NFR-001).
- Suite negativa: nível 6, grant expirado, argumentos alterados.
- Suite de injection na CI (NFR-005).
