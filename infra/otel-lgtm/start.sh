#!/bin/sh
# Arranque do grafana/otel-lgtm do KAI (M03 E2.2; ADR-0017). Endurece as
# predefinições da imagem, que é um "tudo-em-um" de desenvolvimento:
# - o Grafana vem com acesso anónimo de papel Admin: desligado, com uma
#   password de admin obrigatória e forte (sem valor por omissão);
# - a imagem descarrega plugins da internet no arranque: desligado, tal como
#   as verificações de actualizações, os snapshots externos e o Gravatar;
# - o Grafana, o Loki, o Tempo e o Pyroscope enviam estatísticas de uso para
#   stats.grafana.org por omissão: desligadas em todos.
# A password nunca é impressa nem fica no ambiente dos processos: vai para um
# ficheiro 0400 que só o Grafana lê ($__file{}).
# Rever o /otel-lgtm/run-*.sh da imagem a cada mudança de digest: o
# endurecimento depende de ele só definir os GF_* que não existam.
set -eu

pw="${KAI_GRAFANA_ADMIN_PASSWORD:-}"
case "$pw" in
  "") echo "otel-lgtm: falta KAI_GRAFANA_ADMIN_PASSWORD (gera com scripts/dev/passwords.sh)" >&2; exit 1 ;;
  changeme*) echo "otel-lgtm: KAI_GRAFANA_ADMIN_PASSWORD tem o valor de exemplo" >&2; exit 1 ;;
  *[!A-Za-z0-9._-]*) echo "otel-lgtm: KAI_GRAFANA_ADMIN_PASSWORD só aceita [A-Za-z0-9._-]" >&2; exit 1 ;;
esac
if [ "${#pw}" -lt 24 ]; then
  echo "otel-lgtm: KAI_GRAFANA_ADMIN_PASSWORD tem menos de 24 caracteres" >&2
  exit 1
fi

umask 077
mkdir -p /tmp/kai-grafana
printf '%s' "$pw" > /tmp/kai-grafana/admin_password
chmod 0400 /tmp/kai-grafana/admin_password
unset KAI_GRAFANA_ADMIN_PASSWORD pw

export GF_SECURITY_ADMIN_USER=admin
# Expandido pelo próprio Grafana; os outros processos só herdam o caminho.
file_ref='$__file{/tmp/kai-grafana/admin_password}'
export GF_SECURITY_ADMIN_PASSWORD=$file_ref
export GF_AUTH_ANONYMOUS_ENABLED=false
export GF_AUTH_DISABLE_LOGIN_FORM=false
export GF_PLUGINS_PREINSTALL_DISABLED=true
export GF_ANALYTICS_REPORTING_ENABLED=false
export GF_ANALYTICS_CHECK_FOR_UPDATES=false
export GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false
export GF_NEWS_NEWS_FEED_ENABLED=false
export GF_SNAPSHOTS_EXTERNAL_ENABLED=false
export GF_SECURITY_DISABLE_GRAVATAR=true
export LOKI_EXTRA_ARGS="-reporting.enabled=false"
export TEMPO_EXTRA_ARGS="-reporting.enabled=false"
export PYROSCOPE_EXTRA_ARGS="-usage-stats.enabled=false"

exec /otel-lgtm/entrypoint.sh /otel-lgtm/run-all.sh
