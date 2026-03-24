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

After flashing, on the **same Wi‑Fi as the ESP32 STA** (your home LAN):

| Page | URL |
|------|-----|
| Full camera UI (sidebar) | **`http://elegoo-car.local/`** |
| Drive + stream + buttons | **`http://elegoo-car.local/drive`** |
| MJPEG only | **`http://elegoo-car.local:81/stream`** |

If **`elegoo-car.local`** does not resolve (some routers block mDNS), use the **STA IP** printed on USB serial (`STA connected, IP: …`) instead of `elegoo-car.local`.

**Soft AP** (PC joined to `ELEGOO-…` Wi‑Fi): **`http://192.168.4.1/`** and **`http://192.168.4.1/drive`** (stream at **`:81/stream`**).

The `/drive` page shows MJPEG from **port 81** and sends commands via **`POST /elegoo_cmd`** to `Serial2`. **Buttons can move the car** — secure the chassis before testing.

See `docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md` for what changed and why.
