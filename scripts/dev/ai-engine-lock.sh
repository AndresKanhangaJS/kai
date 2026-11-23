#!/usr/bin/env bash
# Regenera os locks do apps/ai-engine (requirements*.txt) com hashes, num
# contentor descartável (P-021). O uv é só a ferramenta de lock, não uma
# dependência do projecto, e vem da imagem oficial fixada por digest (raiz de
# confiança dos hashes; revisão de segurança da E3.2). --no-build: nunca corre
# código de sdists para obter metadados. O contentor só vê cópias dos .in.
# Cutoff de 14 dias: --exclude-newer.
# Uso: scripts/dev/ai-engine-lock.sh <AAAA-MM-DD>   (data limite de publicação)
set -euo pipefail
cd "$(dirname "$0")/../.."
cutoff=${1:?indica a data limite de publicação (AAAA-MM-DD), 14 dias antes de hoje}
[[ $cutoff =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "data inválida: $cutoff"; exit 1; }

python_image=python:3.14.9-slim-trixie@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8
uv_image=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490

work=$(mktemp -d)
cid=""
trap 'rm -rf "$work"; [ -n "$cid" ] && docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT

cid=$(docker create "$uv_image" --version)
docker cp "$cid:/uv" "$work/uv" >/dev/null
cp apps/ai-engine/requirements.in apps/ai-engine/requirements-dev.in "$work/"

docker run --rm -v "$work:/w" -w /w -e CUTOFF="$cutoff" -u "$(id -u):$(id -g)" -e HOME=/tmp \
  "$python_image" sh -c '
  set -e
  for f in requirements requirements-dev; do
    ./uv pip compile --quiet --no-build --generate-hashes --python-version 3.14 \
      --exclude-newer "${CUTOFF}T00:00:00Z" --no-header --output-file "$f.txt" "$f.in"
  done
'
cp "$work/requirements.txt" "$work/requirements-dev.txt" apps/ai-engine/
echo "✓ locks regenerados (cutoff $cutoff)"
