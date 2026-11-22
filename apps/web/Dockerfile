# syntax=docker/dockerfile:1

# Node 24 LTS (decisão do owner, 2026-11-22, M02 E2.2): o Node 20 está em fim
# de vida desde 2026-04-30, e o Vitest 5 / jsdom 31 exigem Node >= 22.
# Fixada por digest (supply chain, security.md); actualizar o digest é uma
# alteração revista, não automática.
FROM node:24-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
