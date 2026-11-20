# ADR-0005: Memória e RAG: MySQL, Qdrant e object storage

- **Estado:** Aceite
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.5, p.6, p.11; ADR-0002, 0008; D-07; P-009, P-014

## Contexto
O PDF define a divisão de responsabilidades entre stores:
- o MySQL é a fonte de verdade [C p.11];
- o Qdrant guarda vectores e não substitui a base relacional [C p.11];
- o object storage guarda os binários e o MySQL os metadados [C p.11].

Exige também que:
- as permissões sejam aplicadas na recuperação [C p.11];
- a indexação seja assíncrona e idempotente [C p.11];
- os dados de utilizadores diferentes estejam isolados [C p.11];
- a memória seja controlável pelo owner [C p.5].

## Opções consideradas
1. **Texto dos chunks no MySQL e vectores no Qdrant**, com payload de tenant e re-verificação no MySQL.
2. **Texto dos chunks só no Qdrant.** Uma escrita a menos. Contra: duas fontes de verdade, e o apagamento fica frágil.
3. **Uma colecção Qdrant por utilizador.** Isolamento físico. Contra: não escala, e a documentação do Qdrant recomenda partição por payload.

## Decisão
- **Opção 1.**
- **MySQL:** guarda `memories`, `knowledge_documents` e `document_chunks` (texto, hash, página).
- **Qdrant:** uma colecção por modelo de embedding e versão, com payload `user_id` indexado como tenant e ainda `source_id`, `doc_id` e `chunk_id`.
- **Retrieval:**
  - exige um filtro de dono imposto pelo código;
  - re-verifica cada hit no MySQL antes de o pôr no prompt.
- **IDs dos pontos:** determinísticos (UUIDv5 de `doc_id`, `sha256`, `pipeline_version`, `embedding_model` e `ordinal`), por isso escrever é sempre um upsert.
- **Memória de longo prazo:** na v1, só com confirmação do owner.
- **Fora de âmbito aqui:** o modelo de embedding (P-009) e o dono dos chunks (P-014).

## Consequências
- **Positivas:** apagar é seguro mesmo com atraso de sincronização; não há duplicados ao re-indexar.
- **Negativas:** a re-verificação acrescenta alguns ms; mudar de embedding obriga a re-indexar para uma colecção nova.

## Verificação
- Teste: 0 resultados de outro dono (NFR-009).
- Re-indexar não duplica pontos.
- Apagar remove o documento do MySQL, do Qdrant e do storage (NFR-010).

## Fontes
- qdrant.tech/documentation/guides/multiple-partitions, verificado a 2026-11-20.
