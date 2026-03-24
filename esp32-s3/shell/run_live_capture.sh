#!/usr/bin/env bash
# Continuous multi-stream capture for the ELEGOO ESP32-S3 + UNO stack.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${ELEGOO_VENV:-$ROOT/.venv}/bin/python3"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python venv at ${PYTHON_BIN%/python3}."
  echo "Run: python3 -m venv \"$ROOT/.venv\" && \"$ROOT/.venv/bin/pip\" install -r \"$ROOT/requirements.txt\""
  exit 1
fi

exec "$PYTHON_BIN" "$ROOT/scripts/elegoo_live_capture.py" "$@"
