# ADR-0012: Idioma do repositório: PT-PT

- **Estado:** Aceite (2026-11-20, D-01)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.19

## Contexto
- O PDF recomenda um "README em inglês com visão, funcionalidades e quick start" para o repositório público [C p.19].
- O owner decidiu que todos os artefactos do repositório ficam em português europeu (D-01).

## Opções consideradas
1. **Tudo em PT-PT, incluindo o README.** Coerente com o PDF de produto e com o owner. Contra: menos alcance internacional.
2. **PT-PT com o README em inglês.** Cumpre a p.19, mas mistura idiomas.
3. **Tudo em inglês.** Alcance máximo, mas é a língua que o owner não escolheu.

## Decisão
- **Opção 1.** Docs, ADRs, `CLAUDE.md`, regras, skills, subagentes, descrições de commits e o README ficam em PT-PT.
- Ficam em inglês, por serem sintaxe ou convenção técnica:
  - os identificadores de código;
  - os tipos Conventional Commits (`feat`, `fix`, …);
  - os nomes de ficheiros, skills e subagentes;
  - os termos técnicos consagrados.

## Consequências
- **Positivas:** um só idioma, alinhado com o PDF e com o owner.
- **Negativas:** desvio à p.19; menos leitores fora do mundo lusófono. É reversível: pode acrescentar-se um `README.en.md` mais tarde, com um ADR que substitua este.

## Verificação
- A revisão (`kai-review`) e o `kai-docs-writer` verificam o idioma dos artefactos novos.
