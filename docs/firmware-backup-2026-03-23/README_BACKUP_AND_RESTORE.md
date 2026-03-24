# ELEGOO Smart Robot Car V4 — local backup (read-only capture)

**Created (UTC):** 2026-03-23 (folder name includes local timestamp)  
**Hardware paths used:**  
- **Arduino UNO (ATmega328P)** → USB serial: `CH340-class` → `/dev/cu.usbserial-3120`  
- **ESP32-S3 (camera / Wi‑Fi)** → USB-C CDC → `/dev/cu.usbmodemD0CF132BCB181` (when enumerated)

This backup was taken with **read-only** tools only (no erase / write / flash to the boards).

---

## What the 2024 kit PDF adds (same as prior V4 PDFs)

From `01 For Mac and Ubuntu Building a Developed Environment（20220322）.pdf` in **ELEGOO Smart Robot Car Kit V4.0 2024.01.30**:

- Install Arduino IDE on macOS / Ubuntu (download from arduino.cc).
- Open the main `.ino` under `02 Manual & Main Code & APP\...\SmartRobotCarV4.0.ino` (path in PDF uses Windows separators).
- **Important:** use the car’s physical switch: **Upload** while programming the **UNO**; **Cam** when using the **app / camera** path.

That switch behavior is why you may need **Upload** engaged for reliable UNO serial tools.

---

## Exact images you can trust from this capture

### ATmega328P (main UNO) — **authoritative**

| File | Description |
|------|-------------|
| `01_.../atmega328p_flash_32KiB.hex` | Intel HEX of **entire** flash (includes sketch + **Optiboot** in the bootloader region). |
| `01_.../atmega328p_flash_32KiB.bin` | **Raw 32,768 bytes** — bit-for-bit equivalent of the HEX. **Use this to verify SHA-256.** |

**SHA-256 (flash binary):** see `SHA256SUMS.txt` in this folder (key `atmega328p_flash_32KiB.bin`).

This is the **only** on-car MCU image we can certify as a **full, exact** snapshot using the USB bootloader connection.

### ATmega328P — **NOT trustworthy over serial bootloader**

The following were read with the same connection, but **must not be trusted** for “exact chip state” without an **ISP / high-voltage** programmer:

| File | Issue |
|------|--------|
| `atmega328p_eeprom_*` | **Matches the first 1024 bytes of flash** — typical when the **Optiboot** path does not truly expose EEPROM. Treat as **invalid** for EEPROM restore. |
| `atmega328p_{l,h,e}fuse.hex`, `lock`, `*_1B.bin` | Read as **0x00** — **not plausible** for a live Uno; **serial fuse read is not reliable** here. |

**Implication:** restoring “everything” for the UNO over USB is **flash image** (above). EEPROM/fuses need **ISP** if you require a provably exact chip-level clone.

---

## ESP32-S3 (USB-C) — **not captured from the car**

`esptool` could **not** enter the ROM serial bootloader on `/dev/cu.usbmodem...` from this environment (`No serial data received`). Use a project-local Python venv with `esptool` (see repo `requirements.txt`) for retrying the commands in `NOT_CAPTURED_esptool_no_sync.txt`. Common fixes (manual, **no wipe**):

1. Put ESP32-S3 into **download mode**: hold **BOOT**, tap **RESET**, release **BOOT**; rerun `esptool flash-id` / `read_flash`.
2. Close anything holding the port (Serial Monitor, other apps).
3. Try a **data-capable** USB-C cable / different port.

**Factory / kit reference (not read from the vehicle):** see your kit under  
`02 Manual & Main Code & APP/04 Code of Carmer (ESP32)/...` for **source** to rebuild what Elegoo ships — that is **not** a dump of what is currently on your module.

---

## Restore UNO flash from this backup (when you choose to)

**Warning:** writing flash replaces firmware; only do this when you intend to revert.

```bash
AVRDUDE="$HOME/Library/Arduino15/packages/arduino/tools/avrdude/8.0.0-arduino1/bin/avrdude"
CONF="$HOME/Library/Arduino15/packages/arduino/tools/avrdude/8.0.0-arduino1/etc/avrdude.conf"
PORT=/dev/cu.usbserial-3120   # adjust if different

# Car switch → Upload. Then:
"$AVRDUDE" -C "$CONF" -p atmega328p -c arduino -P "$PORT" -b 115200 \
  -U flash:w:"$(pwd)/01_ATmega328P_Arduino_UNO_USB-Serial_CH340/atmega328p_flash_32KiB.hex":i
```

Verify after restore by re-reading flash and comparing SHA-256 to `SHA256SUMS.txt`.

---

## Integrity

See `SHA256SUMS.txt` for cryptographic hashes of backed-up artifacts (binary files live outside this source-only repo).
