# Agent Notes

## 2026-03-24 1

- Goal: build an evidence-backed protocol reference for the ELEGOO V4.0 ESP32-S3 camera firmware and UNO app-control firmware.
- Scope chosen from source, not from prior chat plans:
  - ESP32-S3 camera bridge:
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/02 Manual & Main Code & APP/04 Code of Carmer (ESP32)/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino`
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/02 Manual & Main Code & APP/04 Code of Carmer (ESP32)/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp`
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/02 Manual & Main Code & APP/04 Code of Carmer (ESP32)/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp`
  - UNO app-control firmware:
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/03 Tutorial & Code/08 SmartRobotCarV4.0_DIY and Program on APP/SmartRobotCarV4.0_V1_20220303/SmartRobotCarV4.0_V1_20220303.ino`
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/03 Tutorial & Code/08 SmartRobotCarV4.0_DIY and Program on APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp`
    - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/03 Tutorial & Code/08 SmartRobotCarV4.0_DIY and Program on APP/SmartRobotCarV4.0_V1_20220303/DeviceDriverSet_xxx0.h`

## 2026-03-24 2

- Verified ESP32 TCP bridge behavior from numbered source lines:
  - `WiFiServer server(100)` on line 13.
  - Incoming TCP payload is read byte-by-byte, stripped of spaces inside a brace-delimited frame, and forwarded to `Serial2` unless it equals `{Heartbeat}`.
  - ESP32 emits `{Heartbeat}` to the TCP client every 1000 ms and disconnects after more than 3 missed acknowledgements.
  - ESP32 sends `{"N":100}` to the UNO on disconnect and also if no soft-AP stations remain.
- Evidence file:
  - `/Users/lukekensik/coding/elegoo-comma-1/ELEGOO Smart Robot Car Kit V4.0 2024.01.30/02 Manual & Main Code & APP/04 Code of Carmer (ESP32)/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino`

## 2026-03-24 3

- Verified camera HTTP endpoint registration by machine extraction plus manual line inspection.
- Extracted URIs from `app_httpd.cpp`:
  - `/`
  - `/status`
  - `/control`
  - `/capture`
  - `/stream`
  - `/bmp`
  - `/xclk`
  - `/reg`
  - `/greg`
  - `/pll`
  - `/resolution`
  - `/Test`
  - `/test1`
  - `/test2`
- Important nuance:
  - Only a subset is actually registered on `camera_httpd`.
  - `stream_httpd` is started after incrementing `config.server_port` by 1, so `/stream` is served on the next port after the main camera server.

## 2026-03-24 4

- Verified the default HTTP server port from the installed Arduino ESP32 S3 core header, not from repo comments.
- `HTTPD_DEFAULT_CONFIG()` sets `.server_port = 80`.
- Because ELEGOO increments `config.server_port += 1` before starting `stream_httpd`, the stream server port computes to `81`.
- Evidence file:
  - `/Users/lukekensik/Library/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.7/include/esp_http_server/include/esp_http_server.h`

## 2026-03-24 5

- Verified ESP32 AP behavior:
  - Board notes specify `ESP32S3 Dev Module`, `USB CDC On Boot -> Enabled`, `Flash Size -> 8MB`, `Partition Scheme -> 8M with spiffs (3MB APP/1.5MB SPIFFS)`, `PSRAM -> OPI PSRAM`.
  - Camera code constructs SSID as base `ssid` prefix plus MAC-derived suffix.
  - AP mode is used, not STA mode, in stock firmware.
  - `WiFi.softAP(..., password, 9)` fixes channel 9 in stock firmware.

## 2026-03-24 6

- Verified UNO serial-command parser:
  - `ApplicationFunctionSet_SerialPortDataAnalysis()` accumulates until `}`.
  - It deserializes JSON using `StaticJsonDocument<200>`.
  - Command selector is `doc["N"]`.
  - Optional request serial tag is `doc["H"]`.
- This is the authoritative command entry point for the app-control sketch.

## 2026-03-24 7

- Verified command IDs handled by the UNO app-control sketch:
  - `1`, `2`, `3`, `4`, `5`, `7`, `8`, `21`, `22`, `23`, `100`, `101`, `102`, `105`, `106`, `110`.
- Verified by both manual reading and a small Python extraction over `case <number>:` lines in the handler region.

## 2026-03-24 8

- Verified motion-direction enum and rocker mapping:
  - Motion enum order is zero-based in C++, but comments document the intended user-facing values as 1 through 9.
  - Rocker command `N=102` maps `D1` values 1..9 to:
    - 1 forward
    - 2 backward
    - 3 left
    - 4 right
    - 5 left-forward
    - 6 left-backward
    - 7 right-forward
    - 8 right-backward
    - 9 stop and return to standby

## 2026-03-24 9

- Verified speed boundaries from source:
  - Motor driver header defines `speed_Max 255`.
  - Motion-control comments describe speed as `0~255`.
  - Linear correction path clamps left/right motor outputs to a minimum of `10`.
  - Some higher-level modes cap corrected outputs to `180`.
- Important nuance:
  - The parser itself does not validate `D1`/`D2` ranges before assigning them.
  - Therefore the protocol doc should distinguish "documented or intended range" from "enforced in parser".

## 2026-03-24 10

- Verified stock camera `/control` endpoint shape:
  - Requires query params `var` and `val`.
  - Known adjustable keys include `framesize`, `quality`, `contrast`, `brightness`, `saturation`, `gainceiling`, `colorbar`, `awb`, `agc`, `aec`, `hmirror`, `vflip`, `awb_gain`, `agc_gain`, `aec_value`, `aec2`, `dcw`, `bpc`, `wpc`, `raw_gma`, `lenc`, `special_effect`, `wb_mode`, `ae_level`, and `led_intensity`.
- This is camera tuning only. It is separate from the TCP:100 bridge used for car-motion commands.

## 2026-03-24 11

- Constraint note:
  - No live hardware was attached in this turn, so no runtime wire-level validation was possible.
  - All claims in the reference are therefore limited to:
    - direct source inspection
    - line-numbered extraction
    - local installed SDK/header verification
    - machine-assisted enumeration of commands and URIs
- The protocol reference should say this clearly instead of overstating certainty.
