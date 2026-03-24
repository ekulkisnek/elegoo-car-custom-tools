# WORKING WEBUI — why the ESP32-S3 camera page loads in the browser

This document records **exactly** what was wrong, **exactly** what we changed, and the **workflow** we use for this project (build, flash, verify in a browser). It complements `FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md`, which covers **home Wi‑Fi (STA)** and the **TCP bridge** to the car MCU.

---

## Symptoms before the fix

- **Ping** to the module’s LAN IP could succeed, and **TCP connect** to port **80** could succeed, but **HTTP** failed in confusing ways: **`curl`** or a browser **hung** or saw **connection reset** after sending a normal **`GET /`**.
- Sometimes the **main page HTML** appeared to load, but the **live preview stayed blank** because the stock gzipped UI loads **`/stream`** from the **same origin** as the page (port **80**), not from a second port.

---

## Root cause 1 — WebSocket flags on every HTTP route (primary fix)

**Arduino ESP32 core 3.3.x** ships with **`CONFIG_HTTPD_WS_SUPPORT`** enabled in the prebuilt `sdkconfig` (e.g. `sdkconfig.h` contains `#define CONFIG_HTTPD_WS_SUPPORT 1`).

The ELEGOO / Espressif **camera web server** code in `app_httpd.cpp` wraps URI tables with:

```c
#ifdef CONFIG_HTTPD_WS_SUPPORT
    ,
    .is_websocket = true,
    ...
#endif
```

So **every** registered handler (including **`/`**, **`/stream`**, **`/status`**, …) was marked as a **WebSocket** URI. The HTTP server then expects a **WebSocket upgrade** handshake. A normal browser or `curl` sends a plain **HTTP/1.1 GET**. That mismatch leads to **failed handshakes**, **RST**, or **no HTTP response** — not a subtle CSS bug.

**Fix:** Set **`.is_websocket = false`** for **all** of those standard HTTP handlers (same file, same `#ifdef` blocks). After that, **`GET /`** returns **200** with the gzipped HTML, and the control panel behaves as intended.

**Files:** `esp32-s3/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp`

---

## Root cause 2 — `/stream` must exist on the same port as the main UI

The stock **gzipped index** references **`/stream`** as a **relative URL** on the **same host and port** as the page (typically **port 80**). The upstream sketch often registers **MJPEG** only on a **second** `httpd` instance (e.g. port **81**). Then the sidebar loads, but the **preview iframe** points at **`http://<ip>:80/stream`**, which was never served → **blank video**.

**Fix:** Register the **`stream_uri`** handler on the **primary** `camera_httpd` (port **80**) as well as the optional second server (port **81** for compatibility). Same file: `app_httpd.cpp` → `startCameraServer()`.

---

## Workflow we use on this project

### 1. Source tree

- **Canonical sketch + patches** live under this repo:  
  `elegoo-car-custom-tools/esp32-s3/ESP32_CameraServer_AP_2023_V1.3/`
- The large **ELEGOO vendor ZIP** on disk is **not** committed here; we only track **our** changes (see top-level `README.md`).

### 2. Wi‑Fi credentials (local only)

1. Copy `secrets.h.example` → **`secrets.h`** in the same sketch folder.
2. Set **`HOME_WIFI_SSID`** and **`HOME_WIFI_PASS`** to your **2.4 GHz** network (ESP32 has no 5 GHz radio).
3. **`secrets.h` is gitignored** — never commit real passwords.

### 3. Build with `arduino-cli`

From the sketch directory (or pass the path):

```bash
SK="/path/to/elegoo-car-custom-tools/esp32-s3/ESP32_CameraServer_AP_2023_V1.3"
FQBN="esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600"
arduino-cli compile --fqbn "$FQBN" "$SK"
```

Install the **esp32** platform and board support first if needed (`arduino-cli core install esp32:esp32`).

### 4. Flash over USB

1. Connect the ESP32-S3 (data-capable USB cable).
2. Find the serial device (macOS example: **`/dev/cu.usbmodem…`**).
3. Upload:

```bash
arduino-cli upload -p /dev/cu.usbmodemXXXX --fqbn "$FQBN" "$SK"
```

Use the **Upload** speed in the FQBN or your usual ELEGOO **Notes.txt** if different.

### 5. How we confirm the Web UI (same LAN as the ESP32 STA)

After boot, the module should join **home Wi‑Fi** and print **`STA connected, IP: …`** on **USB serial** (115200 baud). Then:

| What | URL / check |
|------|-------------|
| **Camera UI** | `http://<STA-ip>/` or **`http://elegoo-car.local/`** if mDNS works on your network |
| **Drive + stream page** | `http://<STA-ip>/drive` |
| **MJPEG** | `http://<STA-ip>/stream` (port **80**; **`:81/stream`** may still work) |
| **No mDNS** | Use the **numeric STA IP** from serial or your router DHCP list; **`arp -a`** can show the ESP MAC **`d0:cf:13:…`** → IP |
| **Soft AP only** | Join **`ELEGOO-…`** Wi‑Fi, then **`http://192.168.4.1/`** |

**Quick sanity checks from a PC:**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 "http://<STA-ip>/"
# expect: 200
```

Serial also prints a **`--- net ---`** line every ~20s with STA vs soft-AP hints (see `ESP32_CameraServer_AP_2023_V1.3.ino`).

### 6. PlatformIO (optional)

This folder includes **`platformio.ini`**. PlatformIO uses **`CONFIG_LED_ILLUMINATOR_ENABLED=0`** in `build_flags` to avoid LEDC API drift vs Arduino CLI; use **`pio run`** / **`pio run -t upload`** if you prefer. **Arduino CLI** remains the reference flow for “match ELEGOO Notes” builds.

---

## Summary table

| Issue | Fix |
|------|-----|
| HTTP reset / hang on `GET /` | **`is_websocket = false`** on all normal HTTP URIs under `CONFIG_HTTPD_WS_SUPPORT` |
| Blank video on main page | Register **`/stream`** on **port 80** `httpd`, not only on 81 |
| No LAN IP | Valid **`secrets.h`**, 2.4 GHz SSID, STA join (see STA/bridge doc) |

---

## See also

- `docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md` — STA + AP concurrent mode, `Serial2` bridge, idle logic.
- `esp32-s3/ESP32_CameraServer_AP_2023_V1.3/README.md` — short sketch README and URL table.
