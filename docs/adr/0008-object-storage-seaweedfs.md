# ADR-0008: Object storage: SeaweedFS via API S3

- **Estado:** Aceite (2026-11-20, D-12)
- **Data:** 2026-11-20
- **Decisores:** owner
- **Relacionados:** PDF p.7, p.11, p.15; ADR-0005, 0007

## Contexto
- O PDF propõe o MinIO para binários [C p.11, p.15].
- A 2026-11-20, o repositório `minio/minio` está arquivado (desde 25 Abr 2026), marcado como "NO LONGER MAINTAINED", e a edição comunitária é distribuída só em código-fonte, sem binários.
- O object storage só é necessário a partir do M04, quando chegam documentos.

## Opções consideradas
1. **SeaweedFS** (Apache-2.0; release 4.54 a 16 Nov 2026; gateway S3). Activo e com licença permissiva.
2. **Garage** (AGPLv3). Feito para self-hosting pequeno; não confirmámos a última release.
3. **RustFS.** Ainda em fase de preview.
4. **Ceph RGW.** Desproporcionado para um utilizador.
5. **Cloudflare R2** (gerido). Bom para produção em cloud, mas não serve para desenvolvimento local.

## Decisão
- Usamos **SeaweedFS** em local e na VPS, e o código só fala a API S3 (disco `s3` no Laravel, boto3 no Python).
- O R2 fica como opção de produção em cloud.
- Um teste de contrato S3 (presign, multipart, delete) garante que se pode trocar de backend.
- Entra no M04.

## Consequências
- **Positivas:** não dependemos de software abandonado; trocar de backend é barato.
- **Negativas:** desvio ao PDF; temos de seguir a evolução do SeaweedFS.

## Verificação
- Teste de contrato S3 na CI a partir do M04.

## Fontes (verificadas a 2026-11-20)
- github.com/minio/minio
- github.com/seaweedfs/seaweedfs
- github.com/deuxfleurs-org/garage
- github.com/rustfs/rustfs
