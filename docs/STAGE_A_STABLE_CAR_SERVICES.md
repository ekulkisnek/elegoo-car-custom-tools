# Stage A: Stable car services — milestone

**Goal:** reliable Wi‑Fi, camera stream, and TCP control.

**Done when (acceptance):**

| Criterion | Status |
|-----------|--------|
| Camera stream stable from Mac (browser / MJPEG) | **PASSED** |
| TCP port **100** stable (LAN control path to car MCU) | **PASSED** |
| Continuous capture / long runs without repeated ESP dropouts | **PASSED** |

This milestone reflects the firmware + workflow state in this repo as of the matching git tag/commit, not an automated CI gate.

---

## Technical details (how we got here)

### Wi‑Fi (STA + soft AP)

- **`WIFI_AP_STA`:** ELEGOO soft AP (`ELEGOO-` + MAC) stays up for the stock app; **station mode** joins the home **2.4 GHz** router using **`secrets.h`** (`HOME_WIFI_SSID` / `HOME_WIFI_PASS`).
- **Association:** bounded wait loop (~60 s) with serial progress; prints **STA IP** and channel on success.
- **Stability knobs:** `WiFi.setSleep(false)`, higher TX power (`WIFI_POWER_19_5dBm`), **`WiFi.setHostname("elegoo-car")`**, **mDNS** advertising **http** on ports **80** and **81**.
- **Implementation:** `CameraWebServer_AP.cpp` (radio mode and `WiFi.begin` sequencing—not only the `.ino`).

### Camera Web UI and MJPEG stream

- **Arduino ESP32 3.3.x** enables **`CONFIG_HTTPD_WS_SUPPORT`**. Stock **`app_httpd.cpp`** marked every URI with **`is_websocket = true`**, which breaks plain **HTTP GET** to **`/`** and **`/stream`**. **Fix:** **`is_websocket = false`** for all normal HTTP handlers.
- **Same-origin stream:** gzipped index loads **`/stream`** on **port 80**. **`stream_uri`** is registered on the **primary** `camera_httpd` (port 80), not only the secondary server on 81.
- **Files:** `esp32-s3/ESP32_CameraServer_AP_2023_V1.3/app_httpd.cpp`.

### TCP port 100 (bridge to UNO / car MCU)

- **`WiFiServer server(100)`** in `ESP32_CameraServer_AP_2023_V1.3.ino` accepts JSON from the LAN; forwards to **`Serial2`** at **9600** baud.
- **Idle / standby bugfix:** stock logic treated “no soft‑AP stations” as disconnected. With **STA** in use, **LAN** clients are on STA while **soft AP station count** may be **0**. The condition was tightened so standby / `{"N":100}` only applies when **STA is not connected** *and* there are **no** soft‑AP clients—preserving **TCP 100** sessions for home‑network control.

### Verification workflow (manual)

- **Flash:** `arduino-cli` with ESP32-S3 FQBN (8M flash, OPI PSRAM, etc.); USB **`/dev/cu.usbmodem*`**.
- **HTTP:** `curl` or browser to **`http://<STA-ip>/`**, **`/stream`**, **`/drive`**; **`elegoo-car.local`** when mDNS works.
- **TCP 100:** client connects to **`WiFi.localIP():100`** from the same LAN; observe no spurious bridge teardown during LAN‑only use.

See also: **`docs/WORKING_WEBUI.md`**, **`docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md`**.
