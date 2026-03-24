#!/usr/bin/env bash
# Phase 1 — Layer-3 checks from a PC on the same LAN as the ESP32 STA (or on ELEGOO soft AP).
# Usage: ./run_layer3_connectivity.sh <hostname_or_ip>
set -euo pipefail
HOST="${1:?usage: $0 <ip_or_hostname>}"
echo "# Layer-3 matrix — host: $HOST — $(date -u +%Y-%m-%dT%H:%MZ)"
echo ""
echo "| Check | Result |"
echo "|-------|--------|"
if ping -c 1 -W 1 "$HOST" &>/dev/null; then ping_r="ok"; else ping_r="fail"; fi
echo "| ping | $ping_r |"
http_code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 4 "http://$HOST/" 2>/dev/null || true)
if [[ -z "$http_code" || "$http_code" == "000" ]]; then http_code="fail"; fi
echo "| curl :80 | HTTP $http_code |"
out100=$(nc -vz -w 3 "$HOST" 100 2>&1 || true)
if echo "$out100" | grep -qiE 'succeeded|open\.'; then nc100="ok"; else nc100="fail"; fi
echo "| nc :100 | $nc100 — $out100 |"
out22=$(nc -vz -w 3 "$HOST" 22 2>&1 || true)
if echo "$out22" | grep -qiE 'succeeded|open\.'; then nc22="ok"; else nc22="fail"; fi
echo "| nc :22 | $nc22 — $out22 |"
echo ""
echo "If :80 ok but :22 fail: SSH not in flash, ELEGOO_ENABLE_SSH 0, elegoo_ssh_init skipped, or crash (Serial [SSH])."
