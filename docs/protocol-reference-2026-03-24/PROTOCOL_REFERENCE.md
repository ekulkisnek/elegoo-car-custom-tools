# ELEGOO V4.0 Protocol Reference

Evidence basis:

- This document is derived from direct source inspection of the stock ELEGOO ESP32-S3 camera firmware and the UNO app-control firmware included in the local `2024.01.30` kit tree.
- Supporting extraction work and intermediate findings are logged in [AGENT_NOTES.md](/Users/lukekensik/coding/elegoo-comma-1/elegoo-car-custom-tools/docs/protocol-reference-2026-03-24/AGENT_NOTES.md).
- No live hardware was exercised during this pass, so runtime behavior is documented only where it is directly evidenced by source or local installed SDK headers.

## Firmware Pair

ESP32-S3 camera and network bridge:

- [`ESP32_CameraServer_AP_2023_V1.3.ino`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino)
- [`CameraWebServer_AP.cpp`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp)
- [`app_httpd.cpp`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp)

UNO app-control firmware:

- [`SmartRobotCarV4.0_V1_20220303.ino`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/SmartRobotCarV4.0_V1_20220303.ino)
- [`ApplicationFunctionSet_xxx0.cpp`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp)
- [`DeviceDriverSet_xxx0.h`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/DeviceDriverSet_xxx0.h)

## Architecture

The stock control path is a two-hop bridge:

1. A TCP client connects to the ESP32-S3 on port `100`.
2. The ESP32 reads brace-delimited frames from TCP and forwards most of them to the UNO over `Serial2`.
3. The UNO parses those frames as JSON and dispatches on `doc["N"]`.

Evidence:

- TCP bridge server declaration at [`ESP32_CameraServer_AP_2023_V1.3.ino:13`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:13)
- Forwarding from TCP to `Serial2` at [`ESP32_CameraServer_AP_2023_V1.3.ino:37`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:37) and [`ESP32_CameraServer_AP_2023_V1.3.ino:58`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:58)
- UNO JSON parser entrypoint at [`ApplicationFunctionSet_xxx0.cpp:1771`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1771)
- UNO main loop invoking the parser at [`SmartRobotCarV4.0_V1_20220303.ino:32`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/SmartRobotCarV4.0_V1_20220303.ino:32)

## ESP32 Transport

### TCP bridge

- Port: `100`
- Source: [`ESP32_CameraServer_AP_2023_V1.3.ino:13`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:13)

Frame rules observed in source:

- Frames are brace-delimited.
- Spaces inside an active frame are dropped by the ESP32 bridge before forwarding.
- `{Heartbeat}` is consumed by the ESP32 bridge and is not forwarded to the UNO.
- Any other completed frame is forwarded to `Serial2` unchanged after whitespace stripping.

Evidence:

- Frame start and end logic at [`ESP32_CameraServer_AP_2023_V1.3.ino:41`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:41)
- Space removal at [`ESP32_CameraServer_AP_2023_V1.3.ino:45`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:45)
- Heartbeat special-case at [`ESP32_CameraServer_AP_2023_V1.3.ino:52`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:52)

### Heartbeat behavior

- ESP32 sends `{Heartbeat}` to the TCP client every 1000 ms.
- If the client fails to answer with `{Heartbeat}` for more than 3 consecutive checks, the ESP32 breaks the session.

Evidence:

- Heartbeat transmit and counter logic at [`ESP32_CameraServer_AP_2023_V1.3.ino:76`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:76)
- Disconnect threshold at [`ESP32_CameraServer_AP_2023_V1.3.ino:89`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:89)

### Failsafe stop behavior

The ESP32 emits `{"N":100}` to the UNO in three cases:

- when the TCP loop ends after a client disconnect
- when the soft-AP station count drops to zero during an active client session
- when no client is connected after a previously connected state

Evidence:

- AP station drop case at [`ESP32_CameraServer_AP_2023_V1.3.ino:102`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:102)
- Disconnect cleanup at [`ESP32_CameraServer_AP_2023_V1.3.ino:109`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:109)
- No-client fallback at [`ESP32_CameraServer_AP_2023_V1.3.ino:115`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:115)

## Camera Networking

### Wi-Fi mode

The stock ESP32 firmware operates as a soft AP, not a station client.

Evidence:

- AP mode at [`CameraWebServer_AP.cpp:156`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp:156)
- AP creation at [`CameraWebServer_AP.cpp:157`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp:157)

### AP naming

- The visible Wi-Fi name is built from a base `ssid` prefix plus a MAC-derived suffix.
- The suffix assigned to `wifi_name` is the MAC-derived part only.

Evidence:

- MAC-derived naming logic at [`CameraWebServer_AP.cpp:139`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp:139)
- `wifi_name` assignment at [`CameraWebServer_AP.cpp:153`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp:153)

### AP channel

- The stock AP is started on channel `9`.
- Evidence: [`CameraWebServer_AP.cpp:157`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp:157)

## Camera HTTP Endpoints

### Server ports

- Main camera web server: port `80`
- Stream server: port `81`

Evidence chain:

- `HTTPD_DEFAULT_CONFIG()` in the locally installed ESP32 S3 Arduino core sets `.server_port = 80` in [`esp_http_server.h:53`](/Users/lukekensik/Library/Arduino15/packages/esp32/tools/esp32s3-libs/3.3.7/include/esp_http_server/include/esp_http_server.h:53)
- ELEGOO starts `camera_httpd` with that default config at [`app_httpd.cpp:1211`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1211) and [`app_httpd.cpp:1386`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1386)
- ELEGOO increments `config.server_port += 1` before starting `stream_httpd` at [`app_httpd.cpp:1403`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1403)

### Registered endpoints

Registered on the main camera server:

- `/`
- `/status`
- `/control`
- `/capture`
- `/Test`
- `/test1`
- `/test2`

Evidence:

- Handler registration at [`app_httpd.cpp:1387`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1387)

Registered on the stream server:

- `/stream`

Evidence:

- Stream server registration at [`app_httpd.cpp:1406`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1406)

Defined but not registered in the stock build as checked here:

- `/bmp`
- `/xclk`
- `/reg`
- `/greg`
- `/pll`
- `/resolution`

Evidence:

- URI definitions at [`app_httpd.cpp:1280`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1280)
- Registration lines are commented out at [`app_httpd.cpp:1391`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:1391)

### `/control` endpoint

The stock camera control endpoint expects query parameters:

- `var`
- `val`

Evidence:

- Query parsing at [`app_httpd.cpp:771`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:771)

Recognized `var` keys in the checked build:

- `framesize`
- `quality`
- `contrast`
- `brightness`
- `saturation`
- `gainceiling`
- `colorbar`
- `awb`
- `agc`
- `aec`
- `hmirror`
- `vflip`
- `awb_gain`
- `agc_gain`
- `aec_value`
- `aec2`
- `dcw`
- `bpc`
- `wpc`
- `raw_gma`
- `lenc`
- `special_effect`
- `wb_mode`
- `ae_level`
- `led_intensity`

Evidence:

- Command list in [`app_httpd.cpp:786`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp:786)

## UNO JSON Command Protocol

### Frame format

The UNO parser expects a JSON object terminated by `}` and deserializes it using ArduinoJson.

Known keys used by the parser:

- `N`: command ID
- `H`: optional command serial number or request tag
- `D1`, `D2`, `D3`, `D4`: command-specific parameters
- `T`: command-specific timer value

Evidence:

- Parser setup at [`ApplicationFunctionSet_xxx0.cpp:1773`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1773)
- JSON deserialization at [`ApplicationFunctionSet_xxx0.cpp:1801`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1801)
- `N` and `H` extraction at [`ApplicationFunctionSet_xxx0.cpp:1810`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1810)

### Command map

`N=1`

- Meaning: motor control mode
- Params:
  - `D1`: motor selection
  - `D2`: motor speed
  - `D3`: motor direction
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1817`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1817)

`N=2`

- Meaning: car movement control with time limit
- Params:
  - `D1`: direction
  - `D2`: speed
  - `T`: duration or timer value
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1828`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1828)

`N=3`

- Meaning: car movement control without time limit
- Params:
  - `D1`: direction
  - `D2`: speed
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1839`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1839)

`N=4`

- Meaning: direct left and right motor speed control
- Params:
  - `D1`: left speed
  - `D2`: right speed
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1848`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1848)

`N=5`

- Meaning: servo control
- Params:
  - `D1`: servo selector
  - `D2`: servo angle
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1856`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1856)

`N=7`

- Meaning: lighting control with time limit
- Params:
  - `D1`: lighting sequence
  - `D2`: red
  - `D3`: green
  - `D4`: blue
  - `T`: duration
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1864`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1864)

`N=8`

- Meaning: lighting control without time limit
- Params:
  - `D1`: lighting sequence
  - `D2`: red
  - `D3`: green
  - `D4`: blue
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1878`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1878)

`N=21`

- Meaning: ultrasonic sensor status request
- Param:
  - `D1`: request mode or selector
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1890`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1890)

`N=22`

- Meaning: line-tracking sensor status request
- Param:
  - `D1`: request mode or selector
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1897`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1897)

`N=23`

- Meaning: query whether the car has left the ground
- Response shape:
  - `{<H>_false}` when `Car_LeaveTheGround == true`
  - `{<H>_true}` when `Car_LeaveTheGround == false`
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1904`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1904)

`N=100`

- Meaning: clear all functions and enter standby mode
- This is also the stop command used by the ESP32 bridge on disconnect conditions.
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1925`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1925)

`N=101`

- Meaning: switch to one of the built-in car modes
- `D1` mapping:
  - `1`: trace mode
  - `2`: obstacle avoidance mode
  - `3`: follow mode
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1933`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1933)

`N=102`

- Meaning: rocker control mode command
- Param:
  - `D1`: rocker direction code
- `D1` mapping:
  - `1`: forward
  - `2`: backward
  - `3`: left
  - `4`: right
  - `5`: left-forward
  - `6`: left-backward
  - `7`: right-forward
  - `8`: right-backward
  - `9`: stop and return to standby
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1983`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1983)

`N=105`

- Meaning: FastLED brightness adjustment
- `D1` mapping:
  - `1`: increase brightness by 5 while below 250
  - `2`: decrease brightness by 5 while above 0
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1953`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1953)

`N=106`

- Meaning: preset servo-position command
- Param:
  - `D1`: servo preset index
- Parser-enforced bound:
  - valid only for `1..5`
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1970`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1970)

`N=110`

- Meaning: clear all functions and enter programming mode
- Evidence: [`ApplicationFunctionSet_xxx0.cpp:1919`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1919)

## Direction Codes

The firmware’s documented direction order is:

- `1`: forward
- `2`: backward
- `3`: left
- `4`: right
- `5`: left-forward
- `6`: left-backward
- `7`: right-forward
- `8`: right-backward
- `9`: stop

Evidence:

- Enum comments at [`ApplicationFunctionSet_xxx0.cpp:54`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:54)
- Motion-control parameter comment at [`ApplicationFunctionSet_xxx0.cpp:200`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:200)

## Speed Semantics

Documented or intended bounds:

- Generic motor maximum: `255`
- Movement comments document speed range as `0..255`

Evidence:

- `speed_Max 255` in [`DeviceDriverSet_xxx0.h:112`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/DeviceDriverSet_xxx0.h:112)
- `speed range is 0~255` in [`ApplicationFunctionSet_xxx0.cpp:147`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:147)

Observed control nuances:

- The UNO command parser does not clamp most incoming speed fields when reading JSON.
- The straight-line correction path clamps corrected motor outputs to a minimum of `10`.
- Several modes reduce the upper limit to `180` for corrected movement.

Evidence:

- Parser assignments without validation at [`ApplicationFunctionSet_xxx0.cpp:1818`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1818)
- Minimum clamp to `10` at [`ApplicationFunctionSet_xxx0.cpp:176`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:176)
- Mode-based upper limits at [`ApplicationFunctionSet_xxx0.cpp:213`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:213)

## Ack and Response Behavior

Observed response patterns:

- Some commands respond with `{<H>_ok}` when `_is_print` is enabled.
- `N=100` responds with `{ok}` in the checked build.
- `N=23` responds with `{<H>_true}` or `{<H>_false}` depending on leave-the-ground state.
- The ESP32 bridge forwards complete `Serial2` brace-delimited responses back to the TCP client.

Evidence:

- Generic forwarding back to TCP at [`ESP32_CameraServer_AP_2023_V1.3.ino:64`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino:64)
- Per-command responses in [`ApplicationFunctionSet_xxx0.cpp:1817`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/03%20Tutorial%20%26%20Code/08%20SmartRobotCarV4.0_DIY%20and%20Program%20on%20APP/SmartRobotCarV4.0_V1_20220303/ApplicationFunctionSet_xxx0.cpp:1817)

## Board and Build Notes

For the stock ESP32-S3 camera sketch, the local `Notes.txt` specifies:

- Board: `ESP32S3 Dev Module`
- `USB CDC On Boot`: enabled
- Flash size: `8MB`
- Partition scheme: `8M with spiffs (3MB APP/1.5MB SPIFFS)`
- PSRAM: `OPI PSRAM`

Evidence:

- [`Notes.txt:1`](/Users/lukekensik/coding/elegoo-comma-1/ELEGOO%20Smart%20Robot%20Car%20Kit%20V4.0%202024.01.30/02%20Manual%20%26%20Main%20Code%20%26%20APP/04%20Code%20of%20Carmer%20%28ESP32%29/ESP32-S3-WROOM-1-Camera/ESP32_CameraServer_AP_2023_V1.3/Notes.txt:1)

## Confidence Notes

High-confidence items in this reference:

- TCP port `100`
- heartbeat cadence and disconnect threshold
- `N` command IDs handled by the UNO app-control sketch
- registered camera URIs
- main web port `80` and stream port `81`
- direction-code mapping for rocker mode

Lower-confidence items that still need live hardware confirmation:

- exact response payloads seen by a TCP client in a full end-to-end session
- whether all camera URIs behave identically on the shipped binary as in source
- practical bounds accepted by the mobile app for each `N` command

Recommended next runtime validation, if hardware is connected later:

1. Connect to TCP `:100` and capture heartbeat and stop-command behavior.
2. Issue one known-safe command such as `{"N":100}` and observe the returned frame.
3. Confirm `http://<ap-ip>/`, `http://<ap-ip>/status`, `http://<ap-ip>/capture`, and `http://<ap-ip>:81/stream`.
