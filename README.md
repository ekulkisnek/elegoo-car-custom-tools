# ELEGOO Smart Robot Car V4 — custom tools & notes

This repository holds **only personal tooling and documentation** for working with the **ELEGOO Smart Robot Car Kit V4.0** (ESP32-S3 camera module + Arduino UNO stack). It does **not** include the ELEGOO vendor firmware tree, PDFs, or large third-party projects—those stay in the official kit ZIP or upstream repos.

If you clone this repo, pair it with:

- **ELEGOO Smart Robot Car Kit V4.0** (e.g. `2024.01.30` release) for the stock `SmartRobotCarV4.0.ino`, `ESP32_CameraServer_AP_2023_V1.3`, manuals, and APP assets.
- **Arduino ESP32 board support** and **arduino-cli** (or Arduino IDE) for builds.

---

## What problem this repo solves

1. **Repeatable diagnostics** — Shell scripts to check LAN connectivity, optional SSH, serial boot logs, and `arduino-cli` compile sanity without hunting through a multi-gigabyte kit folder.
2. **Isolated WiFi testing** — A tiny **soft-AP-only** sketch so you can tell whether RF/WiFi stack issues are separate from camera/web firmware.
3. **Resilient ESP32 flash backup** — A Python script that reads the whole SPI flash in **1 MiB chunks with retries**, which is easier on flaky USB than one long `read_flash`.
4. **Firmware backup provenance** — Documented notes from a **read-only** capture session (UNO flash, ESP32 capture failures, SHA-256 manifest, and warnings about EEPROM/fuse reads over the bootloader).

Nothing here replaces ELEGOO’s documentation; it **supplements** your own workflow.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `scripts/esp32_full_flash_backup_chunked.py` | Chunked full SPI read for **ESP32-S3** via `esptool`; writes `output/` + a small manifest. |
| `esp32-s3/shell/*.sh` | Bash helpers: connectivity, toolchain/SSH checks, optional LDT automation, WiFi sanity. |
| `esp32-s3/WiFi_AP_SmokeTest/` | Minimal Arduino sketch: broadcasts `ELEGOO-SMOKE` soft AP (no camera). |
| `docs/firmware-backup-2026-03-23/` | Notes, checksums, and failure logs from the March 2026 backup session (text only; binary dumps are not in git). |
| `docs/WORKING_WEBUI.md` | **Camera Web UI:** why HTTP works on Arduino ESP32 3.3+ (`CONFIG_HTTPD_WS_SUPPORT` / `is_websocket`), `/stream` on port 80, and the **build → flash → browser** workflow we use. |
| `docs/STAGE_A_STABLE_CAR_SERVICES.md` | **Stage A milestone:** stable Wi‑Fi + camera stream + TCP/100; acceptance checklist (PASSED) and technical summary. |
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

- ELEGOO **ZIP** / full **manual + code** tree  
- **openpilot** or other large upstream projects  
- **Prebuilt** `arduino-cli` binaries, **venv** directories, **build output**  
- **Firmware binaries** (use `.gitignore`; store separately if needed)

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
