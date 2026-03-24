# ELEGOO Smart Robot Car V4 — custom tools & notes

This repository holds **personal tooling, firmware patches, and documentation** for the **ELEGOO Smart Robot Car Kit V4.0** (ESP32-S3 camera + Arduino UNO) and for **bridging [commaai/openpilot](https://github.com/commaai/openpilot)** to the car over the stock **TCP/100** path. It does **not** vendor the full ELEGOO ZIP, full openpilot tree, or large binaries—those stay in the kit release, upstream clones, or private storage.

**Resume / project state:** see **`ELEGOO-PROJECT-STATE.md`** at this repo root (stages, gaps, copy-paste commands). **Current bottleneck:** **Stage E** — tuning control so the car behaves **safely and predictably** under openpilot (torque → motor commands, safety stops, asymmetry). **Stage F** — richer **synthetic feedback** into openpilot (`carState`) when real telemetry from the stock stack is limited.

If you clone this repo, pair it with:

- **ELEGOO Smart Robot Car Kit V4.0** (e.g. `2024.01.30` release) for stock sketches, manuals, and APP assets.
- **Arduino ESP32** board support and **arduino-cli** (or IDE) for ESP32-S3 builds.
- A separate **openpilot** checkout (e.g. sibling `openpilot/`) if you use the bridge or **`openpilot-mods/`** patches—see **`ELEGOO-PROJECT-STATE.md`** for layout.

---

## What the stack does today (functionalities)

| Piece | Role |
|------|------|
| **ESP32-S3** | Wi‑Fi (home STA + `ELEGOO-…` soft AP), **HTTP** camera UI + MJPEG, **TCP :100** JSON bridge to the UNO |
| **Arduino UNO** | Motor control from the stock **JSON** protocol (`N=4` torque-style commands, `N=100` stop, etc.) |
| **Mac / PC** | Flash tooling, **`elegoo_motor_test_suite.py`** (gated motor tests), **openpilot** + Python **bridge** (sendcan → TCP) when configured |
| **openpilot (dev)** | Webcam road camera (Stage B patches under **`openpilot-mods/`**), **card** / torque messaging — bridge consumes **`TORQUE_L` / `TORQUE_R`** and maps to ELEGOO-side speeds |

Remaining work is not “more GPIO” but **control quality** (Stage E) and **believable state feedback** (Stage F) so the closed loop feels stable.

---

## Current challenges: Stage E (control tuning) — in progress

**Goal:** tune control so the car behaves **safely and predictably** under openpilot.

### What needs tuning

**Torque-to-speed mapping** — Openpilot outputs **`TORQUE_L` / `TORQUE_R`** in comma/body units; the ELEGOO expects **PWM-like** speed values. You need: a **scale** factor, **clipping**, **sign** handling, and a **neutral deadband**.

**Left/right asymmetry** — Small robots often pull to one side. Expect **left/right bias** correction and optional **per-side scaling**.

**Low-speed behavior** — Avoid **motor chatter** from tiny commands, **sudden jerks** near zero torque, and **oscillation** around standstill.

**Safety behavior** — Always aim for: **stop on bridge exit**, **stop on TCP disconnect**, **stop on stale sendcan**, **stop on invalid state**, and **output rate limiting**.

### Recommended E steps

1. Start with **very conservative** command limits.
2. **Log:** received torque, translated left/right speeds, time, observed motion.
3. **Tune order:** **deadband** first → **overall scale** second → **left/right correction** third → **rate limiting** last.

### Exit criteria (Stage E)

- Car moves **smoothly** under low command values.
- **Straight** commands mostly go **straight**; **turn** commands are **consistent**.
- **Stop** behavior is **immediate** and **reliable**.

Implementation hooks (when present in your workspace) include **`elegoo_control_map.py`**, **`elegoo_openpilot_bridge.py`**, and flags such as **`--torque-scale`**, **`--deadband`**, **`--stale-sendcan-stop`** — see **`ELEGOO-PROJECT-STATE.md`**.

---

## Stage F (feedback / `carState`) — planned

**Goal:** improve the **quality of state** fed back to openpilot so the stack behaves more naturally.

**Reality:** the stock ELEGOO path does not expose **rich real telemetry** in a clean way over TCP, so early feedback will likely be **synthetic**.

**MVP feedback model**

- **Wheel speeds:** derive estimated **`SPEED_L` / `SPEED_R`** from recent translated motor commands (stable and believable, not perfect at first).
- **Standstill:** report standstill when commanded speeds are near zero long enough.
- **Faults:** set fault bits on TCP disconnect, heartbeat failure, unreachable car, bridge exceptions.
- **Battery / charging:** stable **placeholders** first (`BATT_PERCENTAGE`, `CHARGER_CONNECTED`); improve if real data appears.

**Better F later:** simple dynamics (not instant speed assignment), accel ramp, saturation/slip handling, optional vision/timing hints, real telemetry only if worth the complexity.

### Exit criteria (Stage F)

- openpilot receives **stable `carState`**, **no excessive fault flapping**, **consistent** control loop, synthetic state **good enough** to keep the robot controllable.

---

## Recommended execution order

1. Treat **Stage C** (gated motor tests, real-world safety) as the **gate** before trusting automation on the floor.
2. **D.1 / D.2** (bridge plumbing, sendcan path) can proceed **in parallel** with C where safe.
3. After C is proven, run **D.3 live** (bridge + car + openpilot).
4. **Iterate E and F together:** **E** for **command quality**, **F** for **state quality**.

---

## “Minimal easy setup” (target end state)

The simplest version of the final system should be:

1. **Power on** the car.
2. Ensure **camera / TCP :100** reachable on the LAN.
3. Start **one bridge script**.
4. Start **openpilot** in **webcam** mode.
5. **Openpilot drives** through the bridge.

Exact commands and env vars live in **`ELEGOO-PROJECT-STATE.md`** and stage-specific docs under **`docs/`**.

---

## Fresh agent: pick up where we left off

This section is the **onboarding ladder** for someone (or an agent) with **no prior context**. Read **`ELEGOO-PROJECT-STATE.md`** next; it is the **single resume file** for stages, gaps, and copy-paste commands. Some of those commands assume a **parent workspace** (see below).

### 1. Two directory levels (do not confuse them)

| Location | What it is |
|----------|------------|
| **`elegoo-car-custom-tools/`** (this **git** repo) | What you clone from GitHub: ESP32 sketch sources under `esp32-s3/`, Python `scripts/`, `docs/`, `openpilot-mods/`, tests. **This README is the root of this repo.** |
| **Parent folder** (e.g. `elegoo-comma-1/` on the author’s machine) | Optional **workspace** that may sit **next to** this repo and hold **`openpilot/`**, **`scripts/stage-*-verify/`**, **`artifacts/`** — paths referenced inside **`ELEGOO-PROJECT-STATE.md`**. If you only cloned **`elegoo-car-custom-tools`**, those sibling paths may **not** exist; use the state file as a spec and recreate or symlink as needed. |

**Rule:** paths in **`ELEGOO-PROJECT-STATE.md`** are often written from the **parent** workspace root. Paths in **this README** below `esp32-s3/` and `scripts/` are relative to **`elegoo-car-custom-tools/`**.

### 2. First-time setup (machine)

1. **Install [arduino-cli](https://arduino.github.io/arduino-cli/)** and the **esp32** platform: `arduino-cli core install esp32:esp32`.
2. **Python 3.10+** for scripts; create a venv in this repo (see [Setup](#setup-macos--linux)) and `pip install -r requirements.txt`.
3. **Clone** [commaai/openpilot](https://github.com/commaai/openpilot) **separately** if you will run the UI/bridge; apply patches from **`openpilot-mods/`** (see §7).
4. **chmod** shell scripts once: `chmod +x esp32-s3/shell/*.sh` (and any `scripts/*.sh` you add).

### 3. How the hardware maps to software

```
[ Mac / PC ] ──Wi‑Fi LAN──► [ ESP32-S3 ] ──Serial2 @ 9600──► [ Arduino UNO ] ──► motors
                 │              │
                 │              ├── HTTP :80 / :81  → camera UI, MJPEG /stream
                 │              └── TCP :100        → JSON app protocol → UNO
```

- **Firmware you build from this repo** runs on the **ESP32-S3** (camera + Wi‑Fi + bridge). The **UNO** runs ELEGOO stock sketch **`SmartRobotCarV4.0.ino`** (from the kit ZIP — not committed here).
- **Motor commands** are JSON lines over **TCP :100**, forwarded to **`Serial2`**. Details: **`docs/MAC_CONTROLS_CAR.md`**, **`scripts/elegoo_protocol.py`**, **`docs/protocol-reference-2026-03-24/PROTOCOL_REFERENCE.md`**.

### 4. ESP32 firmware: what lives where

| Path | Role |
|------|------|
| **`esp32-s3/ESP32_CameraServer_AP_2023_V1.3/`** | **Canonical** patched camera + bridge sketch (same idea as kit **ESP32-S3-WROOM-1-Camera** tree). |
| **`ESP32_CameraServer_AP_2023_V1.3.ino`** | Entry: `setup`/`loop`, **TCP server :100**, `Serial2` bridge, calls into camera init. |
| **`CameraWebServer_AP.cpp`** | Wi‑Fi **AP+STA**, `WiFi.begin`, `secrets.h`, mDNS, `startCameraServer()`. |
| **`app_httpd.cpp`** | HTTP server: `/`, `/stream`, `/drive`, **`POST /elegoo_cmd`** → `Serial2`. **Critical:** `is_websocket = false` under Arduino 3.3+ `CONFIG_HTTPD_WS_SUPPORT` (see **`docs/WORKING_WEBUI.md`**). |
| **`elegoo_drive_html.h`** | Embedded **/drive** web UI. |
| **`secrets.h`** | **Not in git.** Copy from **`secrets.h.example`** → set **`HOME_WIFI_SSID`** / **`HOME_WIFI_PASS`** (2.4 GHz only). |
| **`platformio.ini`** | Optional **PlatformIO** build; Arduino CLI remains the reference for “match ELEGOO Notes”. |

### 5. Flashing the ESP32 (Arduino CLI, detailed)

**A. One-time credentials**

```bash
cd esp32-s3/ESP32_CameraServer_AP_2023_V1.3
cp secrets.h.example secrets.h
# Edit secrets.h — 2.4 GHz network only
```

**B. Compile**

```bash
SK="$(pwd)"   # or absolute path to ESP32_CameraServer_AP_2023_V1.3
FQBN="esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600"
arduino-cli compile --fqbn "$FQBN" "$SK"
```

**C. Upload** (ESP32-S3 USB; put board in boot mode if upload fails: hold **BOOT**, tap **RESET**, release **BOOT**)

```bash
arduino-cli upload -p /dev/cu.usbmodemXXXX --fqbn "$FQBN" "$SK"
```

Use the correct **`/dev/cu.usbmodem*`** (macOS) or `COMx` (Windows). **115200 baud** for **USB serial** logs.

**D. Verify**

- Serial monitor: **`--- net ---`** lines with STA IP and **`ELEGOO-…`** soft AP SSID.
- Browser: **`http://<STA-IP>/`** or **`http://elegoo-car.local/`** (if mDNS works).
- See **`docs/WORKING_WEBUI.md`** for HTTP/WebSocket and **`/stream`** on port 80.

**E. Optional: PlatformIO** — open the sketch folder in VS Code with PlatformIO; `pio run -t upload`. See **`platformio.ini`** (illuminator may be disabled for PIO vs Arduino).

### 6. Usage: motor tests (no openpilot)

From **`elegoo-car-custom-tools`**:

```bash
source .venv/bin/activate   # if using venv
python3 scripts/elegoo_motor_test_suite.py --host <ESP32_LAN_IP>
```

Interactive guided steps; uses **`elegoo_protocol`** and **N=3 untimed** forward/back on the bridge (see **`docs/MAC_CONTROLS_CAR.md`**). **Clear the area;** the car can move.

**Unit tests:** `pytest tests/test_elegoo_protocol.py` (no hardware).

### 7. openpilot: patches and integration

1. Check out **openpilot** at or near the SHA in **`openpilot-mods/BASE_COMMIT.txt`** (or resolve conflicts if newer).
2. From **openpilot** repo root:  
   `git apply /path/to/elegoo-car-custom-tools/openpilot-mods/patches/stage-b-openpilot-camera.patch`
3. Read **`openpilot-mods/README.md`** for env vars (`USE_WEBCAM`, `NOBOARD`, `OPENPILOT_START_ONROAD`, `OPENPILOT_SKIP_UNBLOCK_STDOUT`, `OPENPILOT_WEBCAM_ALWAYS`).
4. Full **bridge / manager** command lines may live under the **parent workspace** — see **`ELEGOO-PROJECT-STATE.md`** (`run_openpilot_manager_macos.sh`, `run_stage_d_bridge.sh`, etc.). If those scripts are missing locally, use the state file as a **recipe** to recreate them or run Python modules with the same env vars.

**Noise vs blockers:** **`docs/STAGE_D_OPENPILOT_NON_BLOCKERS.md`** (dbus, models, encoderd, dirty tree, …).

### 8. Development workflow (edit → verify)

| Goal | Action |
|------|--------|
| **Change Wi‑Fi / HTTP / bridge** | Edit **`CameraWebServer_AP.cpp`**, **`app_httpd.cpp`**, or `.ino` → **compile** → **flash** → **curl** / browser / **`run_layer3_connectivity.sh`**. |
| **Change JSON protocol** | Edit **`scripts/elegoo_protocol.py`** → run **`pytest`** → run **motor suite** on hardware. |
| **Change openpilot UI/manager** | Edit upstream files → refresh **`stage-b-openpilot-camera.patch`** with `git diff` from a clean tree and commit (or maintain a branch in your openpilot clone). |
| **Document a milestone** | Add/update under **`docs/`** and a line in **`ELEGOO-PROJECT-STATE.md`**. |

Always **`git status`** before commits; **`secrets.h`** and **`output/`** are **gitignored**.

### 9. Safety and staging

- Run **Stage C** (gated motor tests, clear area) before **unsupervised** bridge + openpilot on the floor.
- Prefer **conservative** torque/PWM limits when tuning Stage E.
- **Stop** path: bridge and firmware should send **`N=100`** stop on exit/disconnect when implemented — confirm in **`elegoo_openpilot_bridge.py`** / state doc.

### 10. Documentation index (read in this order for depth)

| Doc | Contents |
|-----|----------|
| **`ELEGOO-PROJECT-STATE.md`** | Stages A–E, gaps, **exact commands** (may assume parent workspace). |
| **`docs/WORKING_WEBUI.md`** | ESP32 HTTP + WebSocket fix, `/stream`, flash workflow. |
| **`docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md`** | STA + soft AP, TCP bridge idle fix. |
| **`docs/STAGE_A_STABLE_CAR_SERVICES.md`** | Stage A acceptance. |
| **`docs/MAC_CONTROLS_CAR.md`** | Mac → TCP/100 → UNO, N=3 motor suite. |
| **`docs/STAGE_B_CAMERA_OPENPILOT.md`** | Webcam in openpilot. |
| **`docs/STAGE_D_OPENPILOT_NON_BLOCKERS.md`** | Log noise reference. |
| **`openpilot-mods/README.md`** | Patch apply + env vars. |
| **`esp32-s3/ESP32_CameraServer_AP_2023_V1.3/README.md`** | Sketch-specific URLs and behavior. |

### 11. Troubleshooting (quick)

| Symptom | Check |
|---------|--------|
| HTTP hangs / reset on `/` | Arduino **3.3+** `is_websocket` fix — **`docs/WORKING_WEBUI.md`**. |
| Ping OK, HTTP fails | Firewall or wrong IP; **ARP** MAC `d0:cf:13:…` for ESP32. |
| TCP :100 drops on LAN | STA+bridge idle logic — **`docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md`**. |
| Motor suite forward/back weird | **N=3** untimed vs **N=2** timed — **`docs/MAC_CONTROLS_CAR.md`**. |
| openpilot “unavailable” / no torque | **`sendcan`** / **card** config — **`ELEGOO-PROJECT-STATE.md`**; not always a bridge bug. |

---

## What problem this repo solves

1. **Repeatable diagnostics** — Shell scripts for LAN, serial, `arduino-cli` compile checks.
2. **Isolated WiFi testing** — Soft-AP-only smoke sketch.
3. **Resilient ESP32 flash backup** — Chunked SPI read with retries.
4. **Firmware backup provenance** — Session notes, hashes, restore cautions.
5. **Camera firmware fixes** — Patched **ESP32-S3** sketch sources (`esp32-s3/...`) for STA + HTTP/WebSocket behavior.
6. **openpilot-on-Mac dev** — **`openpilot-mods/`** patches (webcam, manager, UI) — not a full fork.
7. **Bridge + control roadmap** — Documentation for Stages D–F and **`ELEGOO-PROJECT-STATE.md`** as the living handoff.

Nothing here replaces ELEGOO’s or comma’s upstream docs; it **supplements** your workflow.

---

## Repository layout

| Path | Purpose |
|------|---------|
| **`ELEGOO-PROJECT-STATE.md`** | **Master resume guide** (openpilot ↔ ELEGOO): accomplished stages, remaining gaps, workflows, commands. Paths assume parent workspace `elegoo-comma-1` with `scripts/` and `openpilot/` siblings. |
| `scripts/esp32_full_flash_backup_chunked.py` | Chunked full SPI read for **ESP32-S3** via `esptool`; writes `output/` + a small manifest. |
| `esp32-s3/shell/*.sh` | Bash helpers: connectivity, toolchain/SSH checks, optional LDT automation, WiFi sanity. |
| `esp32-s3/WiFi_AP_SmokeTest/` | Minimal Arduino sketch: broadcasts `ELEGOO-SMOKE` soft AP (no camera). |
| `docs/firmware-backup-2026-03-23/` | Notes, checksums, and failure logs from the March 2026 backup session (text only; binary dumps are not in git). |
| `docs/WORKING_WEBUI.md` | **Camera Web UI:** why HTTP works on Arduino ESP32 3.3+ (`CONFIG_HTTPD_WS_SUPPORT` / `is_websocket`), `/stream` on port 80, and the **build → flash → browser** workflow we use. |
| `docs/STAGE_A_STABLE_CAR_SERVICES.md` | **Stage A milestone:** stable Wi‑Fi + camera stream + TCP/100; acceptance checklist (PASSED) and technical summary. |
| `openpilot-mods/` | **commaai/openpilot** local patches only — **`patches/stage-b-openpilot-camera.patch`** (5 files: manager + UI + **AugmentedRoadView** webcam overlay). See `README.md`. |
| `docs/STAGE_B_CAMERA_OPENPILOT.md` | **Stage B:** camera works in openpilot UI (webcam / NOBOARD / MJPEG); links to patch + env vars. |
| `docs/MAC_CONTROLS_CAR.md` | **Mac → TCP/100 → Serial2 → UNO** path; motor suite uses **N=3 untimed** forward/back (bridge reliability vs N=2 timed). |
| `docs/STAGE_D_OPENPILOT_NON_BLOCKERS.md` | **Stage D:** openpilot moving wheels — symptom→cause table for **non-blocking** log noise (dirty tree, dbus, models, encoderd, PyAV/cv2, EKF, etc.). |
| `README.md` (top sections) | **Living roadmap** + **Fresh agent onboarding** (this file): workspace layout, flash steps, file map, dev loop, doc index, troubleshooting. |
| `scripts/elegoo_protocol.py` | ELEGOO **JSON** over TCP (`N=4`, `N=100` stop, heartbeats) — shared by motor suite and bridge. |
| `scripts/elegoo_motor_test_suite.py` | Interactive **TCP/100** motor tests (gated prompts). |
| `scripts/elegoo_live_capture.py` | Multi-stream logging (serial, TCP, HTTP); used by `run_live_capture.sh`. |
| `scripts/elegoo_openpilot_bridge.py` | **openpilot → TCP** bridge (sendcan / torque); may be untracked until you `git add` it. |
| `scripts/elegoo_control_map.py` | Torque→PWM mapping, stale-sendcan helpers; may be untracked until you `git add` it. |
| `tests/test_elegoo_protocol.py` | **pytest** for protocol helpers (no car). |
| `requirements.txt` | Optional Python deps (`pyserial`, `esptool`) for a local venv. |

---

## Setup (macOS / Linux)

### Arduino / ESP32

Install **arduino-cli**, add the ESP32 core, and install the ESP32-S3 board package you use for the car. Typical smoke-test FQBN (8 MB flash, OPI PSRAM):

```text
esp32:esp32:esp32s3:PartitionScheme=default,PSRAM=opi,CPUFreq=240,FlashMode=qio,FlashSize=8M,UploadSpeed=921600,DebugLevel=none,EraseFlash=none
```

The main ELEGOO camera sketch often uses **`huge_app`** and different partition options—match whatever your kit README recommends when you build **stock** firmware.

### Python (serial + esptool)

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Some scripts default to **`ELEGOO_VENV`** pointing at repo `/.venv-serial` for **pyserial** only; you can set `ELEGOO_VENV` to your `.venv` or create `.venv-serial` if you prefer the old names.

For **chunked flash backup**, the script looks for `repo/.venv-esptool/bin/python3` first, then `repo/.venv`, then the current interpreter.

---

## Tools in detail

### `scripts/esp32_full_flash_backup_chunked.py`

- Reads the entire SPI flash over USB using **`esptool`** in **1 MiB** chunks, retrying each chunk on failure.
- Default output: **`output/esp32s3_spi_flash_full.bin`** (under this repo). Override with `--out`.
- Default port: first **`/dev/cu.usbmodem*`** on macOS; pass `--port` explicitly if needed.
- If output already exists, it is renamed to **`*.previous`** before a new run.
- Writes **`ESP32_FLASH_BACKUP_MANIFEST.txt`** next to the image (SHA-256, bytes, restore hint).

**Requirements:** ESP32-S3 in **download mode** (hold **BOOT**, tap **RESET**, release **BOOT**), port not held by Serial Monitor, data-capable USB cable.

---

### `esp32-s3/shell/run_layer3_connectivity.sh`

Runs from a PC on the **same LAN** as the car (or connected to the ELEGOO soft AP). Argument: **IP or hostname**.

Checks: **ping**, **HTTP :80**, **TCP :100** (app socket), **TCP :22** (SSH if you ever enable it). Prints a Markdown-style table to stdout—useful to paste into a log.

---

### `esp32-s3/shell/run_wifi_sanity_checks.sh`

Requires **ESP32-S3 USB** connected. Uses **`ESP32_PORT`** (default `/dev/cu.usbmodem21201`). Runs **`esptool`** `chip-id`, `flash-id`, `read-mac` if `esptool` is on `PATH` or under **`repo/.venv-esptool/bin/esptool`**.

Always **`arduino-cli compile`** the included **`WiFi_AP_SmokeTest`**.

Optionally set **`ELEGOO_CAMERA_SKETCH`** to the absolute path of the kit folder **`ESP32_CameraServer_AP_2023_V1.3`** to compile the main camera sketch as well.

---

### `esp32-s3/shell/verify_ssh_toolchain.sh`

Prints **arduino-cli** version, **LibSSH**-related libraries in `arduino-cli lib list`, recommended FQBN, and EasyLibSSH paths. If **`ELEGOO_CAMERA_SKETCH`** is set to the kit camera sketch directory, runs a **dry-run compile** (last lines only). Use this when experimenting with **SSH-on-ESP32** builds; stock ELEGOO sketches may not ship with SSH enabled.

---

### `esp32-s3/shell/try_ssh_client.sh`

For **public-key** SSH tests against **`esp32@host`**. Requires **`SSH_KEY`** env var pointing at an **ed25519** private key that matches what the firmware expects.

---

### `esp32-s3/shell/run_ldt_automated_checks.sh`

**“LDT”** session automation: optional compile (if **`ELEGOO_CAMERA_SKETCH`** is set), **ping/curl/nc** to **`elegoo-car.local`**, local route/Wi-Fi sanity, and an **8 s serial capture** at 115200 baud filtered for interesting lines. Writes **`LDT_AUTOMATED_RUN_RESULTS.md`** in the repo root by default (or pass a path as `$1`).

Uses **`ELEGOO_VENV`** for Python (default **`repo/.venv-serial`**) with **pyserial** for the serial read.

### `scripts/elegoo_live_capture.py` + `esp32-s3/shell/run_live_capture.sh`

Continuous capture for the streams that matter most during bring-up:

- **ESP32 USB serial**
- **UNO USB serial**
- **TCP bridge** on port **`100`** with automatic **`{Heartbeat}`** replies
- **HTTP `/status`** polling
- **HTTP `/stream`** monitoring on port **`81`**

Default output goes to **`output/live-capture/<UTC timestamp>/`** with one log per stream plus raw byte captures for serial/TCP. The MJPEG stream is monitored continuously by default and can optionally be saved with **`--save-mjpeg`**.

By default the serial capture follows **`/dev/cu.usbmodem*`** for the ESP32-S3 and **`/dev/cu.usbserial*`** for the UNO, which helps when macOS renumbers the device after a reset.

Example:

```bash
./esp32-s3/shell/run_live_capture.sh --host 192.168.1.123
```

If mDNS is working, you can also use:

```bash
./esp32-s3/shell/run_live_capture.sh --host elegoo-car.local
```

---

### `esp32-s3/WiFi_AP_SmokeTest`

Minimal **Arduino** sketch: **`WIFI_AP`** mode only, SSID **`ELEGOO-SMOKE`**, 115200 serial. Confirms **2.4 GHz soft AP** visibility before you debug the full camera + STA + app pipeline.

**After** testing, re-flash the **ELEGOO camera sketch** from the kit so the car behaves normally.

---

## Integrating the ELEGOO camera sketch (optional)

This repo does **not** copy **`ESP32_CameraServer_AP_2023_V1.3`** (vendor code). To let scripts compile it, set:

```bash
export ELEGOO_CAMERA_SKETCH="/absolute/path/to/ESP32_CameraServer_AP_2023_V1.3"
```

That path is the folder containing **`ESP32_CameraServer_AP_2023_V1.3.ino`**, inside the kit’s **`04 Code of Carmer (ESP32)`** tree.

---

## Firmware backup docs (`docs/firmware-backup-2026-03-23/`)

These files record a **read-only** backup session:

- **`README_BACKUP_AND_RESTORE.md`** — What was captured, what was **not** reliable (EEPROM/fuses over serial), ESP32 bootloader sync failure, and how to **restore UNO flash** with `avrdude` if you choose to.
- **`SHA256SUMS.txt`** — Hashes for **hex/bin/log** and doc files from the original session. Large binaries (e.g. full ATmega flash, ESP32 SPI image) are **not** committed to this git repo; keep them in private storage or a release artifact if you need them.
- **`NOT_CAPTURED_esptool_no_sync.txt`** — Why the on-car ESP32 SPI dump did not complete in that session.
- **`WARNING_EEPROM_AND_FUSES_NOT_VERIFIED.txt`** — Why certain UNO reads should not be trusted for restore.

---

## What is intentionally excluded

- ELEGOO **ZIP** / full **manual + code** tree (use the kit release beside this repo).
- The **full openpilot** checkout — only **`openpilot-mods/patches/*.patch`** and notes are stored here; clone **commaai/openpilot** separately.
- Other large upstream trees (same idea).
- **Prebuilt** `arduino-cli` binaries, **venv** directories, **build output**.
- **Firmware binaries** (use `.gitignore`; store separately if needed).

---

## License

Original ELEGOO sketches and trademarks belong to **ELEGOO**. Code and docs written for this repo are provided as-is for personal use; add a license file if you want to share publicly.

---

## Quick reference

| Task | Command / action |
|------|------------------|
| Chunked ESP32 flash read | `python3 scripts/esp32_full_flash_backup_chunked.py --port /dev/cu.usbmodemXXXX` |
| WiFi + esptool sanity | `./esp32-s3/shell/run_wifi_sanity_checks.sh` |
| LAN / ports | `./esp32-s3/shell/run_layer3_connectivity.sh <ip>` |
| Full LDT report | `./esp32-s3/shell/run_ldt_automated_checks.sh` |
| Smoke-test only | Build/flash `esp32-s3/WiFi_AP_SmokeTest` (see its README) |

Make shell scripts executable once: `chmod +x esp32-s3/shell/*.sh`.
