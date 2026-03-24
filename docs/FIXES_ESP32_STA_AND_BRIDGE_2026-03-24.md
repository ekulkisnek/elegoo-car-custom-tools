# Fixes: ESP32-S3 home Wi‑Fi (STA) + TCP bridge on LAN (2026-03-24)

This note describes the **firmware changes** that made the ELEGOO ESP32-S3 camera module usable on a **home LAN** while keeping the **stock soft AP** path, and why **serial / TCP control** started behaving correctly when the phone or PC was **not** connected to `ELEGOO-…`.

---

## Symptom summary

1. **STA (client) mode** was needed so the module could get a **LAN IP** (browser to `http://<sta-ip>/`, tools talking to TCP port **100** over Wi‑Fi).
2. With STA working, **soft-AP station count** is often **zero** when you control the car from the **home network**. The stock logic treated “no soft-AP clients” as “nobody is connected” and **tore down** the bridge / sent standby inappropriately.

---

## Files and what each fix does

### `esp32-s3/ESP32_CameraServer_AP_2023_V1.3/CameraWebServer_AP.cpp`

**Purpose:** Bring up **concurrent AP + STA** (`WIFI_AP_STA`) and join the home router.

**Changes (conceptual):**

- After building the default **ELEGOO** AP SSID (`ELEGOO-` + MAC) and calling `WiFi.softAP(...)`, the code calls `WiFi.disconnect(...)` (clears stale STA state), then `WiFi.begin(...)` with **home SSID/password** from `secrets.h` (see `secrets.h.example`; real values are **not** committed).
- Uses a **bounded wait loop** (e.g. ~60 s) with `.` progress on serial, then prints **STA IP** and Wi‑Fi channel on success, or a clear failure message while noting the **soft AP remains available**.
- Sets higher TX power and disables modem sleep to reduce flaky associations on 2.4 GHz (still subject to router and RF environment).

**Why it matters:** ELEGOO’s stock tree centers on **soft AP**; “paste `WiFi.begin` only in the `.ino`” is insufficient because **init and HTTP/camera bring-up** live here. This file is the right layer for **radio mode** and **association** sequencing.

### `esp32-s3/ESP32_CameraServer_AP_2023_V1.3/ESP32_CameraServer_AP_2023_V1.3.ino`

**Purpose:** JSON **TCP server on port 100** bridges the app protocol to **`Serial2`** (9600 baud to the main car MCU).

**Bug class:** The periodic check used `WiFi.softAPgetStationNum() == 0` to decide that **no Wi‑Fi client** was attached. In **AP+STA**, a legitimate session may come via **STA** (LAN IP) while **soft-AP has zero stations**. The old test then behaved as if idle and issued **`{"N":100}`** / broke the session.

**Fix:** Only treat “no Wi‑Fi path” as idle when **STA is not connected** *and* there are **no soft-AP stations**:

- `if (WiFi.status() != WL_CONNECTED && WiFi.softAPgetStationNum() == 0)` before stopping / standby.

**Why it matters:** Without this, **heartbeat / idle detection** matches **AP-only** assumptions and breaks **LAN** control even when data is flowing on STA.

### Supporting / unchanged vendor files

The following remain as in the ELEGOO **V1.3** tree for this board and are included for a **complete Arduino sketch folder**: `CameraWebServer_AP.h`, `app_httpd.cpp`, `camera_pins.h`, `camera_index.h`, `Notes.txt`. No separate functional “fix” was required there for the STA/bridge issues above.

---

## Operational notes

- **2.4 GHz only** on ESP32 — use a 2.4 GHz SSID or dual-band router with a distinct 2.4 GHz name if needed.
- **Ground truth** for STA success is **USB serial** logs (IP, association), not only scanning the LAN.
- **Credentials:** use `secrets.h` locally; rotate any password ever pasted into chat or committed by mistake.

---

## Related tooling in this repo

- `scripts/elegoo_motor_test_suite.py` and `scripts/elegoo_protocol.py`: test harness speaking the stock **TCP :100** JSON protocol (includes **heartbeat** handling for long sessions).
- `docs/protocol-reference-2026-03-24/PROTOCOL_REFERENCE.md`: protocol notes derived from firmware inspection.

---

*This document is project notes; it does not replace ELEGOO’s official manuals.*
