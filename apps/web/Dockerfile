# syntax=docker/dockerfile:1

# Node 20: a versão já disponível no ambiente de desenvolvimento local (2026-11-20);
# ainda não fixada por nenhum ADR — rever se vier a precisar de o ser.
FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
