# syntax=docker/dockerfile:1
# AI Engine do KAI (SPEC-004). Base fixada por digest (security.md); as
# dependências instalam-se só a partir dos locks com hashes (P-021).
FROM python:3.14.9-slim-trixie@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin kai
WORKDIR /app

FROM base AS runtime
COPY requirements.txt .
# --only-binary: nunca compila sdists (as dependências de build não teriam hash).
# Sem pip na imagem final: ninguém instala pacotes num contentor comprometido.
RUN pip install --require-hashes --no-deps --only-binary=:all: --root-user-action=ignore -r requirements.txt \
 && python -m pip uninstall -y --root-user-action=ignore pip
COPY src ./src
USER kai
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD ["python", "-I", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=4).status == 200 else 1)"]
CMD ["uvicorn", "kai_ai_engine.main:build", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-server-header"]

# Imagem de qualidade e testes (scripts/ci/ai-engine.sh): corre sem rede.
FROM base AS dev
COPY requirements-dev.txt .
RUN pip install --require-hashes --no-deps --only-binary=:all: --root-user-action=ignore -r requirements-dev.txt
COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests
USER kai
ENV MYPY_CACHE_DIR=/tmp/mypy RUFF_CACHE_DIR=/tmp/ruff
CMD ["sh", "-c", "set -e; echo '→ ruff check'; ruff check --no-cache .; echo '→ ruff format --check'; ruff format --check --no-cache .; echo '→ mypy (strict)'; mypy; echo '→ pytest'; pytest -p no:cacheprovider"]
