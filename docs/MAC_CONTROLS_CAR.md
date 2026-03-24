# Mac controls car successfully — end-to-end path

This note ties together **how a Mac** drives **validated motor commands** to the **ELEGOO car** over the stock **Wi‑Fi bridge**, and why **`elegoo_motor_test_suite.py`** uses specific JSON opcodes.

---

## Data path (Mac → wheels)

1. **Mac** runs Python (e.g. `scripts/elegoo_motor_test_suite.py`) on the **same LAN** as the ESP32 **station** IP.
2. **TCP port 100** — `WiFiServer(100)` on the ESP32 camera module accepts the **ELEGOO app protocol** (JSON lines + `{Heartbeat}`).
3. **ESP32** forwards payloads to **`Serial2`** at **9600 baud** to the **Arduino UNO** on the car.
4. **Firmware** (`ESP32_CameraServer_AP_2023_V1.3.ino`): bridge idle logic only treats the session as idle when **STA is down** *and* **soft‑AP has no clients** — so **LAN-only** control (no phone on `ELEGOO-…`) stays connected (see `docs/FIXES_ESP32_STA_AND_BRIDGE_2026-03-24.md`).

---

## Motor test suite: forward / back use **N=3 untimed**

Linear moves in the guided suite use **`cmd_car_untimed`** (**opcode family N=3**) instead of **`cmd_car_timed`** (**N=2** APP-style timed pulse):

- On **some ESP32 TCP bridge** setups, **N=2 timed** linear commands are **unreliable** or fail to move the car.
- **N=3 untimed** matches the same family as turns / stop flow the bridge already handles well; the **runner prompts** you before sending **`cmd_stop`** so motion does not run unbounded without acknowledgment.

Keys renamed: `timed_forward` → **`untimed_forward`**, `timed_backward` → **`untimed_backward`** (expectation keys unchanged for logging).

---

## Related files

| Path | Role |
|------|------|
| `scripts/elegoo_motor_test_suite.py` | Interactive TCP/100 motor tests |
| `scripts/elegoo_protocol.py` | JSON command builders (`cmd_car_untimed`, etc.) |
| `esp32-s3/.../ESP32_CameraServer_AP_2023_V1.3.ino` | `WiFiServer(100)` + `Serial2` bridge |
| `docs/STAGE_A_STABLE_CAR_SERVICES.md` | TCP/100 + Wi‑Fi stability milestone |

---

## Safety

Clear the area; use **baseline stop** steps; keep hands clear of wheels. The suite is for **bench / controlled** testing.
