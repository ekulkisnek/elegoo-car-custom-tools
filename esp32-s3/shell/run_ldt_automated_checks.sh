#!/usr/bin/env bash
# Run on the Mac that is on the same Wi‑Fi as the car (LDT) and has USB to the ESP32-S3.
# Closes nothing; if serial is empty, quit Arduino Serial Monitor / Cursor serial / other grabbers of the port.
# Optional: ELEGOO_CAMERA_SKETCH=/path/to/ESP32_CameraServer_AP_2023_V1.3 for compile section.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
SKETCH="${ELEGOO_CAMERA_SKETCH:-}"
FQBN="${FQBN:-esp32:esp32:esp32s3:PartitionScheme=huge_app,CPUFreq=240,FlashMode=qio,FlashSize=8M,PSRAM=opi}"
PORT="${ESP32_PORT:-/dev/cu.usbmodem21201}"
VENV="${ELEGOO_VENV:-$REPO_ROOT/.venv-serial}"
OUT="${1:-$REPO_ROOT/LDT_AUTOMATED_RUN_RESULTS.md}"

{
  echo "# LDT automated checks"
  echo "Generated: $(date -u +%Y-%m-%dT%H:%MZ)"
  echo ""
  echo "## 1. Compile"
  echo '```'
  if [[ -n "$SKETCH" && -d "$SKETCH" ]]; then
    arduino-cli compile --fqbn "$FQBN" "$SKETCH" 2>&1 || true
  else
    echo "(skipped — set ELEGOO_CAMERA_SKETCH to kit camera sketch path)"
  fi
  echo '```'
  echo ""
  echo "## 2. LAN / mDNS (must be on **LDT Harmonized Electromagnetism** same subnet as ESP32 STA)"
  echo '```'
  ping -c 2 elegoo-car.local 2>&1 || true
  curl -sS -o /dev/null -w "curl http://elegoo-car.local/ HTTP %{http_code}\n" --connect-timeout 5 http://elegoo-car.local/ 2>&1 || true
  nc -vz -w 3 elegoo-car.local 100 2>&1 || true
  echo '```'
  echo ""
  echo "## 3. Default route / Wi‑Fi (sanity)"
  echo '```'
  route -n get default 2>&1 | head -5 || true
  ifconfig | grep -E "^[a-z].*:.*UP" | head -15 || true
  echo '```'
  echo ""
  echo "## 4. Serial boot (115200, ${PORT})"
  echo "Close other apps using the port first."
  echo '```'
  if [[ -x "$VENV/bin/python3" ]]; then
    "$VENV/bin/python3" - "$PORT" <<'PY'
import sys, serial, time
port = sys.argv[1]
try:
    s = serial.Serial(port, 115200, timeout=0.25)
    s.reset_input_buffer()
    t0 = time.time()
    data = b""
    while time.time() - t0 < 8:
        data += s.read(4096)
    s.close()
    t = data.decode("utf-8", errors="replace")
    print(f"bytes={len(data)}")
    for line in t.splitlines():
        if any(k in line for k in ("HOME WIFI", "ELEGOO network", "mDNS", "Camera Ready", "Soft AP", "STA (LDT)", "CONNECTED", "NOT CONNECTED")):
            print(line)
    if len(data) < 80:
        print("(no text — press RESET on ESP32 with this script running, or port in use)")
except Exception as e:
    print("serial error:", e)
PY
  else
    echo "No venv at $VENV — run: python3 -m venv $VENV && $VENV/bin/pip install pyserial"
  fi
  echo '```'
} | tee "$OUT"
echo "Wrote $OUT"
