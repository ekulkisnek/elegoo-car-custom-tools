# WiFi soft-AP smoke test (ESP32-S3)

Isolates **WiFi only** (no camera, no home-router STA). Use the **same FQBN** as the main camera sketch from the ELEGOO kit when you are done testing.

## Flash

From this repo root, paths are:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600,DebugLevel=none,EraseFlash=none "./esp32-s3/WiFi_AP_SmokeTest"

arduino-cli upload -p /dev/cu.usbmodem21201 --fqbn esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600,DebugLevel=none,EraseFlash=none "./esp32-s3/WiFi_AP_SmokeTest"
```

(Adjust `--fqbn` options to match your environment; replace the port.)

## Interpret

| Phone sees `ELEGOO-SMOKE` | RF + stack OK → focus on main firmware (`wifi_config.h`, country, AP+STA) in the kit sketch. |
|---------------------------|-----------------------------------------------------------------------------|
| No SSID | Antenna, power, 2.4 GHz phone Wi-Fi, or hardware. |

## Serial

115200 baud. Expect `softAP: OK` and `AP IP: 192.168.4.1`.

After testing, **re-flash** the main `ESP32_CameraServer_AP_2023_V1.3` sketch from the ELEGOO **Smart Robot Car Kit V4.0** package.
