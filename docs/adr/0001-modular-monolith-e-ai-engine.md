# ADR-0001: Modular monolith Laravel + AI Engine Python separado

- **Estado:** Proposto
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.7–8; ADR-0002; `docs/product/analysis.md` §5

## Contexto
- O PDF define a estratégia: um Modular Monolith no Core e um AI Engine Python separado [C p.8].
- Outros serviços só se extraem com necessidade de escala independente, isolamento, tecnologia específica, frequência de deploy ou limites operacionais [C p.8].
- Criar muitos microsserviços cedo é um não-objectivo [C p.5].
- O projecto tem uma só pessoa e um só utilizador inicial [C p.2].

## Opções consideradas
1. **Monolito Laravel + AI Engine Python.**
   - Prós: dois deployables; o Python fica no seu ecossistema de IA.
   - Contras: há uma fronteira entre processos para gerir.
2. **Tudo em Laravel**, com chamadas a LLM a partir do PHP.
   - Prós: um só deployable.
   - Contras: ecossistema de IA mais pobre; contradiz o PDF.
3. **Microsserviços desde o início**, com os candidatos da p.8.
   - Contras: custo operacional desproporcionado; viola um não-objectivo.

## Decisão
- Há dois deployables.
- `apps/api` (Laravel 13): módulos por bounded context, sem acesso a tabelas de outros módulos, com fronteiras verificadas por testes de arquitectura.
- `apps/ai-engine` (FastAPI): os serviços candidatos da p.8 ficam como módulos Python até haver evidência medida para os extrair, e cada extracção leva um ADR próprio.

## Consequências
- **Positivas:** operação simples; fronteira de segurança clara (ADR-0004); evolução possível sem reescrever.
- **Negativas:** módulos Python partilham runtime; uma carga pesada (visão, STT) pode afectar o chat. Mitigação: processos de worker separados antes de pensar em extracção.

## Verificação
- Testes de arquitectura no Laravel (M02).
- Revisão (`kai-architect`) de qualquer proposta de novo serviço.
