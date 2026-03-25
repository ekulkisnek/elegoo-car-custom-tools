# ELEGOO ↔ openpilot project — state and resume guide

**Last updated:** 2026-03-25 evening (local)  
**Repo root (this machine):** `/Users/lukekensik/coding/elegoo-comma-1`

This file is the **single place to re-orient** after a break: what works, what is left, and how we work day to day.

---

## What we accomplished

| Area | Status | Notes |
|------|--------|--------|
| **Stage A** — car TCP :100, heartbeat, stock JSON motor protocol | Done (see `STAGE-A-STABLE-CAR-SERVICES.md`, Stage C docs) | ESP ↔ UNO path understood |
| **Stage B** — openpilot on macOS with **webcam/MJPEG** road cam | Done in tooling | `USE_WEBCAM=1`, `run_openpilot_manager_macos.sh`, ESP stream |
| **Stage C** — gated motor tests, motor suite | Done | `elegoo_motor_test_suite.py`, `scripts/stage-c-verify/` |
| **Stage D** — Python **bridge**: `SubMaster(sendcan)` → `PubMaster(can, pandaStates)` → TCP | Done | [`elegoo_openpilot_bridge.py`](elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py), body `carstate` RX fix |
| **Stage E (control tuning + engagement chain)** — deadband, scale, bias, speed clamp, smoothing, stale-sendcan, engagement fixes | Done | [`elegoo_control_map.py`](elegoo-car-custom-tools/scripts/elegoo_control_map.py), CLI flags on bridge |
| **Stage E motor protocol fix** — discovered N=4 is forward-only unsigned speed; switched to N=4 forward + N=3 backward/pivot + N=100 stop | Done | `cmd_motor_pair()` in [`elegoo_protocol.py`](elegoo-car-custom-tools/scripts/elegoo_protocol.py), hardware-verified |
| **Stage F (synthetic feedback)** — estimated wheel speeds, fault state, CAN 516 MOTORS_CURRENT | Done | Bridge derives SPEED_L/R from commanded speed; FAULT bit on TCP disconnect |
| **Unified launcher** | Done | [`run_elegoo_openpilot_full.sh`](scripts/stage-e-verify/run_elegoo_openpilot_full.sh) — starts bridge → manager → optional joystick |
| **Automated verify** | Done | 31 tests across 4 test files: Stage E control (10), Stage D bridge (8), sendcan stale (5), final validation (15) |
| **Full stack live run** | Partially done | All processes green (card, selfdrived, joystickd, etc.), torque flowing to car via N=4, but speed values too low to visibly move wheels — needs tuning |
| **Bench tuning (this session)** | Done | Diagnosed low loop gain (torque_scale=0.35 gave gain 0.24); raised to 2.0 (gain ~0.96). Added `--feedback-alpha` CLI. speed_max=100, deadband=10, accel=0.5. Fixed joystick foreground. Speed sweep poke added. |

---

## What remains / known gaps

| Item | Priority | Notes |
|------|----------|--------|
| **Live bench WASD verification** | HIGH | Run `./scripts/stage-e-verify/run_elegoo_openpilot_full.sh --live --joystick` — joystick now runs foreground. Verify W/S/A/D produce visible wheel motion with new tuned parameters. |
| **Stage E floor tuning** | NEXT | Car on floor — tune `--torque-scale`, `--deadband`, `--bias-l/r`, `--speed-max`, `--smooth-alpha` for straight driving, turning, stops. |
| **Stage F enhancements** | TBD | Add dynamics (acceleration ramp, slip model), integrate real telemetry if ELEGOO provides it. |

---

## Critical technical findings (this session)

### 1. ELEGOO motor command mapping (from firmware source)

The Arduino UNO firmware (`ApplicationFunctionSet_xxx0.cpp`, `DeviceDriverSet_xxx0.cpp`) reveals:

- **N=4** (`CMD_MotorControlSpeed`): Always uses `direction_just` (forward). D1/D2 are **unsigned speed 0-255**. `D1=0, D2=0` calls the stop handler. **Cannot reverse.**
- **N=3** (`CMD_CarControlNoTimeLimit`): Direction enum (1=Left, 2=Right, 3=Forward, 4=Backward) with single speed for both motors.
- **N=1** (`CMD_MotorControl`): Per-motor selection, but passes `direction_void` for the OTHER motor which **sets TB6612 STBY=LOW, disabling the entire motor driver**. Sequential N=1 commands kill each other.
- **N=100**: Stop (sets both motors to `direction_void`, STBY=LOW).
- **Motor A = right wheel, Motor B = left wheel** (confirmed by firmware comments and hardware tests).

### 2. Signed speed mapping

The old mapping (`NEUTRAL_PWM=128`, range 0-255) was wrong. The new mapping:
- Torque [-500, +500] → signed speed [-255, +255] (0 = stop)
- `cmd_motor_pair(speed_l, speed_r)` selects the right ELEGOO command:
  - Both ≥ 0 → N=4 (forward differential, independent per-motor speed)
  - Both ≤ 0 → N=3 backward (average speed, loses differential)
  - Mixed signs → N=3 left/right pivot (average speed)
  - Both = 0 → N=100 stop

### 3. D1/D2 ↔ left/right "swap"

In N=4: `D1 → Motor A (right wheel)`, `D2 → Motor B (left wheel)`. Our bridge passes `speed_l → D1 → right wheel`. This looks swapped, but the full chain (openpilot `TORQUE_L` → `speed_l` → `D1` → right motor) is **consistently** swapped, so turning behavior is correct. Verified by tracing through firmware turn logic.

---

## Workflow (how we work on this repo)

1. **Always `cd` into the repo** before `./scripts/...` (paths are relative to repo root).
2. **Openpilot Python** uses **`openpilot/.venv`** — scripts that run bridge/tests `source` it via wrapper shells.
3. **Three common paths:**
   - **Software only:** run **`run_stage_e_verify.sh`** (or **`run_stage_d_verify.sh`**).
   - **Full stack (software, no car):** `./scripts/stage-e-verify/run_elegoo_openpilot_full.sh`
   - **Full stack (with car):** `CAR_IP=x.x.x.x ./scripts/stage-e-verify/run_elegoo_openpilot_full.sh --live --joystick`
4. **When debugging "no torque":** run **`emit_torque_sendcan.py`** + bridge **dry-run**, or **`run_sendcan_bridge_sanity.sh`**, to separate **messaging** from **openpilot**.
5. **Docs:** stage-specific truth in **`artifacts/stage-*/`** and **`docs/`** under `elegoo-car-custom-tools`; strategy in **`STAGE-D-OPENPILOT-ELEGOO-BRIDGE.md`**.

---

## Exact commands (copy-paste)

Replace `CAR_IP` if your ESP32 is not `192.168.1.191`.

### Full automated test suite (no car, needs `openpilot/.venv`)

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-e-verify/run_stage_e_verify.sh
```

**Look for:** 30 tests pass across control, bridge, sendcan, and final validation test files.

### Full stack: unified launcher (recommended)

**Software only (dry-run, no car required):**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-e-verify/run_elegoo_openpilot_full.sh
```

**With car + keyboard control:**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
export CAR_IP=192.168.1.191
./scripts/stage-e-verify/run_elegoo_openpilot_full.sh --live --joystick
```

### Quick hardware poke tests (car on bench, wheels off ground)

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
python3 scripts/stage-e-verify/hardware_poke.py --host 192.168.1.191 --poke n1_motors
```

### Direct motor test (one-liner, no openpilot needed)

```bash
cd /Users/lukekensik/coding/elegoo-comma-1 && python3 -c "
import socket, time, sys
sys.path.insert(0, 'elegoo-car-custom-tools/scripts')
from elegoo_protocol import cmd_motor_pair, cmd_stop
sock = socket.create_connection(('192.168.1.191', 100), timeout=5)
sock.sendall((cmd_stop() + '\n').encode())
time.sleep(0.3)
for c in cmd_motor_pair(80, 80):
    sock.sendall((c + '\n').encode())
time.sleep(3.0)
try: sock.sendall((cmd_stop() + '\n').encode())
except: pass
sock.close()
"
```

---

## Key file map

| Path | Role |
|------|------|
| [`elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py`](elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py) | Main bridge (CAN, pandaStates, TCP, speed estimation, fault feedback) |
| [`elegoo-car-custom-tools/scripts/elegoo_control_map.py`](elegoo-car-custom-tools/scripts/elegoo_control_map.py) | Torque→signed speed + `sendcan_is_stale` (NEUTRAL_SPEED=0, SpeedSmoother) |
| [`elegoo-car-custom-tools/scripts/elegoo_protocol.py`](elegoo-car-custom-tools/scripts/elegoo_protocol.py) | ELEGOO JSON (`cmd_motor_pair` → N=4/N=3/N=100, `cmd_motor_speed`, `cmd_stop`) |
| [`scripts/stage-e-verify/elegoo_joystick.py`](scripts/stage-e-verify/elegoo_joystick.py) | testJoystick publisher (keyboard WASD / constant) |
| [`scripts/stage-e-verify/run_elegoo_openpilot_full.sh`](scripts/stage-e-verify/run_elegoo_openpilot_full.sh) | Unified launcher (bridge → manager → joystick) |
| [`scripts/stage-e-verify/test_final_validation.py`](scripts/stage-e-verify/test_final_validation.py) | 12 computational tests for live config (speed clamp, stale, PID, feedback, smoothing) |
| [`scripts/stage-e-verify/hardware_poke.py`](scripts/stage-e-verify/hardware_poke.py) | Quick N=1 hardware poke tests (stop, per-motor ID, reverse) |
| [`scripts/stage-b-verify/run_openpilot_manager_macos.sh`](scripts/stage-b-verify/run_openpilot_manager_macos.sh) | Manager launcher (env vars for body fingerprint) |
| [`openpilot/selfdrive/selfdrived/selfdrived.py`](openpilot/selfdrive/selfdrived/selfdrived.py) | Modified: ignores model/DM/planner services for notCar |
| ELEGOO firmware source | `ELEGOO Smart Robot Car Kit V4.0 2024.01.30/02 Manual & Main Code & APP/02 Main Program   (Arduino UNO)/TB6612 & QMI8658C/SmartRobotCarV4.0_V2_20220322/` |

---

## Updating this document

When you finish a milestone, edit the **Last updated** date and the **accomplished** / **remains** tables so the next session starts fast.
