#!/usr/bin/env bash
# E2E de AC-02 (M02 E4.6b) numa stack Docker Compose descartável (`kai-e2e`):
# volumes próprios, apagados no fim; a stack de desenvolvimento fica intacta.
#
# Uso: scripts/e2e.sh   (a partir da raiz do repositório, com a stack de dev parada)
#
# O owner, o segredo TOTP e os códigos de recuperação são sintéticos e só existem
# durante a corrida: passam por variáveis de ambiente, nunca pela linha de
# comandos nem pelo output. Os traces de falhas do Playwright ficam dentro do
# contentor E2E (docker-compose.e2e.yml), que é removido no fim.
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT=kai-e2e
COMPOSE=(docker compose -p "$PROJECT" -f docker-compose.yml -f docker-compose.e2e.yml)
EMAIL=owner@example.test

# A origem WebAuthn obriga às mesmas portas da stack de dev (5173/8000); o MySQL publica a 3306.
for port in 5173 8000 3306; do
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    echo "A porta $port está ocupada (stack de dev ligada?). Pára-a com 'docker compose stop' e repete." >&2
    exit 1
  fi
done

cleanup() {
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "→ A arrancar a stack $PROJECT…"
"${COMPOSE[@]}" up -d --build --wait mysql redis api web

# Instala as dependências antes de existir qualquer segredo no ambiente, e sem
# scripts de instalação (supply chain): os browsers já vêm na imagem.
echo "→ A instalar as dependências do E2E (sem scripts de instalação)…"
"${COMPOSE[@]}" run --rm --no-deps e2e npm ci --ignore-scripts --no-audit --no-fund >/dev/null

echo "→ A migrar a base de dados descartável…"
"${COMPOSE[@]}" exec -T api php artisan migrate --force --no-interaction >/dev/null

echo "→ A criar o owner sintético e a activar o TOTP…"
"${COMPOSE[@]}" exec -T api php artisan kai:create-owner "Owner E2E" "$EMAIL" >/dev/null
totp_output="$("${COMPOSE[@]}" exec -T api php artisan kai:enable-totp "$EMAIL" 2>/dev/null)"

KAI_E2E_TOTP_SECRET="$(sed -n 's/.*secret=\([A-Z2-7]*\).*/\1/p' <<<"$totp_output" | head -n1)"
KAI_E2E_RECOVERY_CODE="$(awk '/Códigos de recuperação/ {getline; gsub(/^ +| +$/, ""); print; exit}' <<<"$totp_output")"
unset totp_output
if [[ -z "$KAI_E2E_TOTP_SECRET" || -z "$KAI_E2E_RECOVERY_CODE" ]]; then
  echo "Não foi possível ler o segredo TOTP do output de kai:enable-totp." >&2
  exit 1
fi
export KAI_E2E_EMAIL="$EMAIL" KAI_E2E_TOTP_SECRET KAI_E2E_RECOVERY_CODE

echo "→ A correr o Playwright…"
# -e NOME sem valor: passa a variável do ambiente, sem a pôr na linha de comandos.
"${COMPOSE[@]}" run --rm \
  -e KAI_E2E_EMAIL -e KAI_E2E_TOTP_SECRET -e KAI_E2E_RECOVERY_CODE \
  e2e

# AC-02a / T-10: cada login fica auditado com o método, e o registo da passkey
# também (T-12). Os logs do api desta stack vão para o stderr do contentor
# (docker-compose.e2e.yml), nunca para o laravel.log da stack de dev.
api_log="$("${COMPOSE[@]}" logs --no-color api)"
count() { grep -c -- "$1" <<<"$api_log" || true; }
passkey_logins=$(count 'auth.login.succeeded.*"method":"passkey"')
totp_logins=$(count 'auth.login.succeeded.*"method":"totp"')
recovery_logins=$(count 'auth.login.succeeded.*"method":"recovery_code"')
failed=$(count 'auth.login.failed')
registered=$(count 'auth.credential.passkey_registered')
echo "→ Auditoria: logins passkey=$passkey_logins totp=$totp_logins recovery_code=$recovery_logins, falhados=$failed, passkeys registadas=$registered."
if [[ "$passkey_logins" -lt 1 || "$totp_logins" -lt 1 || "$recovery_logins" -lt 1 || "$failed" -lt 1 || "$registered" -lt 1 ]]; then
  echo "Auditoria incompleta: falta pelo menos um dos eventos esperados." >&2
  exit 1
fi
# -F (texto literal) e -f (padrões lidos de um descritor): os segredos nunca
# aparecem na linha de comandos do grep.
if grep -qF -f <(printf '%s\n' "$KAI_E2E_TOTP_SECRET" "$KAI_E2E_RECOVERY_CODE") <<<"$api_log"; then
  echo "O log do api contém o segredo TOTP ou um código de recuperação." >&2
  exit 1
fi

echo "✓ E2E de AC-02 a passar."
