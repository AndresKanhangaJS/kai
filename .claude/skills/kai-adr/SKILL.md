---
name: kai-adr
description: Cria ou substitui um Architecture Decision Record (formato MADR) em docs/adr/, com numeração automática e actualização do índice docs/adr/README.md. Usa quando houver uma decisão arquitectural, de tecnologia, de contrato, de segurança ou um desvio ao PDF de produto, ou quando o owner disser "regista a decisão", "cria um ADR", "isto precisa de ADR", "supersede ADR-NNNN", "new ADR".
---
# kai-adr: Architecture Decision Record

## Quando usar
- Escolha de tecnologia ou versão, padrão arquitectural, fronteira entre contextos, contrato, modelo de segurança.
- Qualquer desvio ao PDF de produto (`docs/product/kai-vision.md`).
- Para substituir um ADR `Aceite`. Um ADR aceite **não se edita**; substitui-se por um novo.

## Procedimento
1. Lista `docs/adr/` e calcula o próximo número: o maior `NNNN` + 1, com 4 dígitos.
2. Verifica se já existe um ADR sobre o tema. Se existir e estiver `Aceite`, este ADR vai **substituí-lo**.
3. Copia [templates/adr.md](templates/adr.md) para `docs/adr/NNNN-<titulo-em-kebab>.md`.
4. Preenche:
   - **Contexto**: forças e restrições, com origem ([C] PDF p.N / D-xx, [H], [P]).
   - **Opções consideradas**: pelo menos 2 reais, incluindo a do PDF se divergir.
   - **Decisão**: frase directa, no presente.
   - **Consequências**: positivas, negativas e o que fica mais difícil.
   - **Verificação**: como se sabe que a decisão está a ser cumprida (teste, regra, revisão).
   - Os factos externos (versões, licenças) levam a fonte oficial e a data.
5. O estado é `Proposto`. Só passa a `Aceite` com a aprovação explícita do owner; regista a data.
6. Se substituir outro ADR:
   - o novo leva `Substitui ADR-NNNN`;
   - o antigo recebe **apenas** a linha de estado `Substituído por ADR-MMMM` (é a única edição permitida num ADR aceite).
7. Actualiza a tabela em `docs/adr/README.md`: número, título, estado, data.
8. Mostra ao owner o ADR e o diff do índice.

## Regras
- Uma decisão por ADR. Até ~60 linhas; o detalhe técnico vai para links.
- Nada de decisões escondidas: se o código implementa algo que contraria um ADR, pára e pergunta.
- Escrito em PT-PT. O título começa por um verbo ou substantivo claro ("Usar RabbitMQ…", "Fronteira de…").
