#!/usr/bin/env bash
# Phase 5 — Flash / toolchain sanity for the ELEGOO camera sketch (optional).
# Set ELEGOO_CAMERA_SKETCH to the kit folder containing ESP32_CameraServer_AP_2023_V1.3.ino
set -euo pipefail
echo "=== arduino-cli ==="
command -v arduino-cli && arduino-cli version
echo ""
echo "=== LibSSH-ESP32 (need 5.8.x for ESP32 Arduino 3.x / mbedtls) ==="
arduino-cli lib list | grep -i libssh || true
echo ""
echo "=== Recommended FQBN (8 MB flash on this module) ==="
echo "esp32:esp32:esp32s3:PartitionScheme=huge_app,CPUFreq=240,FlashMode=qio,FlashSize=8M,PSRAM=opi"
echo ""
echo "=== EasyLibSSH path (one of) ==="
echo "  ~/Documents/Arduino/libraries/EasyLibSSH"
echo "  .../ESP32_CameraServer_AP_2023_V1.3/libraries/EasyLibSSH"
echo ""
SKETCH="${ELEGOO_CAMERA_SKETCH:-}"
FQBN="${FQBN:-esp32:esp32:esp32s3:PartitionScheme=huge_app,CPUFreq=240,FlashMode=qio,FlashSize=8M,PSRAM=opi}"
if [[ -n "$SKETCH" && -d "$SKETCH" ]]; then
  echo "=== dry-run compile (SSH on if enabled in your sketch / wifi_config) ==="
  arduino-cli compile --fqbn "$FQBN" "$SKETCH" 2>&1 | tail -5
else
  echo "=== dry-run compile skipped ==="
  echo "Export ELEGOO_CAMERA_SKETCH to your kit camera sketch directory to compile here."
fi
