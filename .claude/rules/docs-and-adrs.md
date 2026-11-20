---
paths:
  - "docs/**"
---
# Documentação e ADRs

- Escreve em PT-PT; termos técnicos consagrados podem ficar em inglês (ex.: *outbox*, *trace*).
- Etiqueta cada afirmação com [C] (cita a página do PDF ou a decisão D-xx), [H] (com justificação) ou [P].
- Nunca preenchas lacunas do PDF: marca-as com `<!-- TODO(owner): ... -->`.
- Factos externos (versões, licenças, sintaxe) levam a fonte oficial e a data de verificação (AAAA-MM-DD).

## ADRs (`docs/adr/`)
- Cria-os com a skill `kai-adr`: formato MADR, ficheiro `NNNN-titulo-em-kebab.md`, numeração sequencial de 4 dígitos.
- Estados possíveis: `Proposto`, `Aceite`, `Rejeitado`, `Obsoleto`, `Substituído por ADR-NNNN`.
- Um ADR `Aceite` não se edita no conteúdo; uma nova decisão cria um ADR que o substitui, e o antigo recebe a ligação.
- Cada ADR tem contexto, decisão, alternativas consideradas e consequências (positivas e negativas).
- Actualiza o índice `docs/adr/README.md` no mesmo commit.

## Estrutura
- `docs/product/`: visão (`kai-vision.md`), análise, PRD.
- `docs/adr/`: decisões.
- `docs/engineering/`: harness e acordos de trabalho.
- `docs/architecture/`: C4 e diagramas, criada quando houver conteúdo (skill `kai-c4`).
- `docs/STATUS.md`: estado actual, actualizado com a skill `/status`.
- Links internos relativos e verificáveis; diagramas em Mermaid dentro do markdown.
