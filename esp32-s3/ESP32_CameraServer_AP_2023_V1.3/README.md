# ESP32-S3 ELEGOO camera — home Wi‑Fi (STA) + soft‑AP

This sketch matches **ESP32-S3-WROOM-1** camera hardware from the ELEGOO Smart Robot Car V4 kit. Build it in Arduino IDE or `arduino-cli` with the **esp32** board package and an **ESP32S3 Dev Module** (or equivalent) profile per ELEGOO `Notes.txt`.

## One-time setup

1. Copy `secrets.h.example` to `secrets.h`.
2. Set `HOME_WIFI_SSID` and `HOME_WIFI_PASS` to your **2.4 GHz** network (ESP32 does not use 5 GHz).

## Behavior

- **Soft AP** remains enabled (`ELEGOO-` + MAC) for the stock phone app / direct link.
- **Station mode** joins your home router when credentials are valid; serial prints the STA IP for browser access to the camera UI.
- The main `.ino` adjusts TCP bridge idle logic so **LAN control** does not disconnect when no clients are on the soft AP.

## Browser drive + stream (same tab)

After flashing, open **`http://<ESP32-IP>/drive`** on the **main HTTP port** (usually 80). The page shows the MJPEG feed from **`http://<same-host>:81/stream`** (camera server uses port +1 for streaming) and **Forward / Back / Left / Right / Stop** buttons. Commands are sent as JSON via **`POST /elegoo_cmd`** to `Serial2` (same as TCP port 100). **Buttons can move the car** — secure the chassis before testing.

See `docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md` for what changed and why.
