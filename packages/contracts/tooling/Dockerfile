# Validador dos contratos (M02 E2.3, ADR-0014). Imagem fixada por digest;
# dependências com versão exacta e hash. Actualizar é uma alteração revista.
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.lock /tmp/requirements.lock
RUN pip install --require-hashes --only-binary=:all: -r /tmp/requirements.lock

RUN useradd --create-home --uid 10001 validator
USER validator
WORKDIR /contracts
ENTRYPOINT ["python", "-I", "/contracts/tooling/validate.py"]
