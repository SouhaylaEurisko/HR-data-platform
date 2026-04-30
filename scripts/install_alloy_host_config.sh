#!/usr/bin/env bash
# Install host Alloy config + env file for HR platform metrics scraping.
#
# Usage:
#   bash scripts/install_alloy_host_config.sh
#   ALLOY_CONFIG_SRC=infra/alloy/config.alloy bash scripts/install_alloy_host_config.sh
#
# This script:
#   1) Creates /etc/alloy if missing
#   2) Copies config to /etc/alloy/config.alloy
#   3) Creates /etc/alloy/grafana-cloud.env from infra/alloy/env.example (if missing)
#   4) Verifies alloy.service references that EnvironmentFile
#   5) Restarts Alloy

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOY_CONFIG_SRC="${ALLOY_CONFIG_SRC:-${ROOT_DIR}/infra/alloy/config.alloy}"
ALLOY_CONFIG_DST="/etc/alloy/config.alloy"
ALLOY_ENV_DST="/etc/alloy/grafana-cloud.env"
ALLOY_ENV_EXAMPLE="${ROOT_DIR}/infra/alloy/env.example"
DROPIN_DIR="/etc/systemd/system/alloy.service.d"
DROPIN_FILE="${DROPIN_DIR}/env.conf"

if [[ ! -f "${ALLOY_CONFIG_SRC}" ]]; then
  echo "ERROR: missing config source: ${ALLOY_CONFIG_SRC}" >&2
  exit 1
fi

if [[ ! -f "${ALLOY_ENV_EXAMPLE}" ]]; then
  echo "ERROR: missing env example: ${ALLOY_ENV_EXAMPLE}" >&2
  exit 1
fi

echo "== Create /etc/alloy if needed"
sudo mkdir -p /etc/alloy

echo "== Install Alloy config"
sudo install -m 0644 "${ALLOY_CONFIG_SRC}" "${ALLOY_CONFIG_DST}"

if [[ ! -f "${ALLOY_ENV_DST}" ]]; then
  echo "== Create ${ALLOY_ENV_DST} from template (fill real values after)"
  sudo install -m 0600 "${ALLOY_ENV_EXAMPLE}" "${ALLOY_ENV_DST}"
else
  echo "== Keep existing ${ALLOY_ENV_DST}"
fi

echo "== Ensure systemd drop-in loads ${ALLOY_ENV_DST}"
sudo mkdir -p "${DROPIN_DIR}"
if [[ ! -f "${DROPIN_FILE}" ]] || ! sudo rg -q "EnvironmentFile=-/etc/alloy/grafana-cloud.env" "${DROPIN_FILE}"; then
  sudo tee "${DROPIN_FILE}" >/dev/null <<'EOF'
[Service]
EnvironmentFile=-/etc/alloy/grafana-cloud.env
EOF
fi

echo "== Reload + restart alloy.service"
sudo systemctl daemon-reload
sudo systemctl restart alloy.service

echo "== Final checks"
sudo systemctl status alloy.service --no-pager | sed -n '1,14p'
echo
echo "Next:"
echo "  1) Edit /etc/alloy/grafana-cloud.env with real GRAFANA_CLOUD_PROMETHEUS_* values"
echo "  2) sudo systemctl restart alloy.service"
echo "  3) sudo journalctl -u alloy.service -n 120 --no-pager"
