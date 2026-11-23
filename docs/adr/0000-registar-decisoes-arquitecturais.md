# ADR-0000: Registar decisões arquitecturais (MADR)

- **Estado:** Aceite
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.19; `.claude/rules/docs-and-adrs.md`

## Contexto
- O PDF exige que as decisões arquitecturais sejam documentadas através de ADRs [C p.5] e publicadas com as alternativas consideradas [C p.19].
- O projecto é público e serve de portfólio: as decisões têm de ser rastreáveis e justificadas.

## Opções consideradas
1. **MADR em `docs/adr/`.** Leve, em markdown, revisto em PR. Contra: exige disciplina para escrever antes de implementar.
2. **Wiki externa.** Fácil de editar. Contra: fica fora do controlo de versões e longe do código.
3. **Sem registo formal.** Zero custo. Contra: decisões implícitas e perda de contexto.

## Decisão
- Usamos MADR em `docs/adr/NNNN-titulo.md`, uma decisão por ADR.
- Estados: Proposto, Aceite, Rejeitado, Obsoleto, Substituído.
- Um ADR aceite é imutável: muda-se criando outro ADR que o substitui.
- Cada ADR regista a proveniência das afirmações ([C]/[H]/[P]).
- O índice é `docs/adr/README.md`; a criação é feita com a skill `kai-adr`.

## Consequências
- **Positivas:** decisões revistas em Git, ligadas a PRs, legíveis por quem visita o repositório.
- **Negativas:** custo de escrita; risco de ADRs desactualizados se não forem substituídos.

## Verificação
- A skill `/done` e a revisão `kai-review` verificam se uma mudança arquitectural traz o seu ADR.
