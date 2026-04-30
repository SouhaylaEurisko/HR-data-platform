#!/usr/bin/env bash
# Smoke-test Phase 6 metrics: /metrics reachable, optional chatbot traffic for agent metrics.
#
# Usage:
#   ./scripts/validate_observability_metrics.sh
#   BACKEND_BASE=http://127.0.0.1:4533 CHATBOT_BASE=http://127.0.0.1:4535 \
#     CHATBOT_USER_ID=1 ./scripts/validate_observability_metrics.sh
#
# With SKIP_CHATBOT_TRAFFIC=1, only checks /metrics (no OpenAI / DB chat flow).

set -euo pipefail

BACKEND_BASE="${BACKEND_BASE:-http://198.244.167.152:4633}"
CHATBOT_BASE="${CHATBOT_BASE:-http://198.244.167.152:4536}"
CHATBOT_USER_ID="${CHATBOT_USER_ID:-1}"
SKIP_CHATBOT_TRAFFIC="${SKIP_CHATBOT_TRAFFIC:-0}"

die() { echo "ERROR: $*" >&2; exit 1; }

echo "== 1) Backend /metrics (expect hr_platform_backend_*)"
code=$(curl -sS -o /tmp/hr_metrics_backend.txt -w "%{http_code}" "${BACKEND_BASE}/metrics") || die "curl backend /metrics failed"
[[ "$code" == "200" ]] || die "backend /metrics HTTP $code"
grep -q "hr_platform_backend" /tmp/hr_metrics_backend.txt || die "no hr_platform_backend_* lines in backend /metrics"
echo "    OK ($(grep -c '^hr_platform_backend' /tmp/hr_metrics_backend.txt || true) lines prefixed hr_platform_backend)"

echo "== 2) Chatbot /metrics (expect hr_platform_chatbot_*)"
code=$(curl -sS -o /tmp/hr_metrics_chatbot.txt -w "%{http_code}" "${CHATBOT_BASE}/metrics") || die "curl chatbot /metrics failed"
[[ "$code" == "200" ]] || die "chatbot /metrics HTTP $code"
grep -q "hr_platform_chatbot" /tmp/hr_metrics_chatbot.txt || die "no hr_platform_chatbot_* lines in chatbot /metrics"
echo "    OK ($(grep -c '^hr_platform_chatbot' /tmp/hr_metrics_chatbot.txt || true) lines prefixed hr_platform_chatbot)"

if [[ "$SKIP_CHATBOT_TRAFFIC" != "1" ]]; then
  echo "== 3) Chatbot traffic (POST /api/conversations/send — exercises FlowAgent + agent metrics)"
  code=$(curl -sS -o /tmp/hr_chat_send.json -w "%{http_code}" \
    -X POST "${CHATBOT_BASE}/api/conversations/send" \
    -H "Content-Type: application/json" \
    -H "X-User-Id: ${CHATBOT_USER_ID}" \
    -d '{"content":"metrics smoke test: hello","sender":"user"}') || die "curl send failed"
  if [[ "$code" != "200" ]]; then
    echo "    WARN: send returned HTTP $code (body in /tmp/hr_chat_send.json). Agent/intent counters may not move."
    cat /tmp/hr_chat_send.json >&2 || true
  else
    echo "    OK HTTP 200"
  fi
  echo "== 4) Re-check chatbot /metrics for agent/intent series (may take one refresh)"
  curl -sS "${CHATBOT_BASE}/metrics" | grep -E 'hr_platform_chatbot_(agent|intent)_' | head -20 || true
else
  echo "== 3–4) Skipped (SKIP_CHATBOT_TRAFFIC=1)"
fi

echo ""
echo "Next (runtime):"
echo "  - Alloy: sudo systemctl status alloy.service && sudo journalctl -u alloy.service -n 50 --no-pager"
echo "  - Grafana Explore (Mimir/Prometheus): hr_platform_backend_http_requests_total"
echo "  - After traffic: rate(hr_platform_chatbot_agent_runs_total[5m])"
