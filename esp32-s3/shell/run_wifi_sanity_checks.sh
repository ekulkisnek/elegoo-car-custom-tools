#!/usr/bin/env bash
# Run from repo machine with ESP32-S3 USB connected. Non-destructive + compile checks.
# Optional: ELEGOO_CAMERA_SKETCH=/path/to/ESP32_CameraServer_AP_2023_V1.3 to also compile main firmware.
set -euo pipefail
PORT="${ESP32_PORT:-/dev/cu.usbmodem21201}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
FQBN="${FQBN:-esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600,DebugLevel=none,EraseFlash=none}"
ESPTOOL="${ESPTOOL:-$(command -v esptool || true)}"
if [[ -z "$ESPTOOL" && -x "$REPO_ROOT/.venv-esptool/bin/esptool" ]]; then
  ESPTOOL="$REPO_ROOT/.venv-esptool/bin/esptool"
fi

echo "=== Port: $PORT ==="
if [[ ! -e "$PORT" ]]; then
  echo "Missing $PORT — plug in the board or set ESP32_PORT."
  exit 1
fi

if [[ -n "${ESPTOOL:-}" && -x "$ESPTOOL" ]]; then
  echo "=== esptool chip-id ==="
  "$ESPTOOL" --chip esp32s3 --port "$PORT" chip-id || true
  echo "=== esptool flash-id ==="
  "$ESPTOOL" --chip esp32s3 --port "$PORT" flash-id || true
  echo "=== esptool read-mac ==="
  "$ESPTOOL" --chip esp32s3 --port "$PORT" read-mac || true
else
  echo "esptool not found; skip chip/flash checks."
fi

echo "=== arduino-cli compile (WiFi_AP_SmokeTest in this repo) ==="
arduino-cli compile --fqbn "$FQBN" "$ROOT/WiFi_AP_SmokeTest"
CAM="${ELEGOO_CAMERA_SKETCH:-}"
if [[ -n "$CAM" && -d "$CAM" ]]; then
  echo "=== arduino-cli compile (ELEGOO_CAMERA_SKETCH) ==="
  arduino-cli compile --fqbn "$FQBN" "$CAM"
else
  echo "(optional) Set ELEGOO_CAMERA_SKETCH to also compile the kit camera sketch."
fi
echo "OK."
