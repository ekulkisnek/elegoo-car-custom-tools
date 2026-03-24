# ELEGOO ↔ openpilot project — state and resume guide

**Last updated:** 2025-03-24 (local)  
**Repo root (this machine):** `/Users/lukekensik/coding/elegoo-comma-1`

This file is the **single place to re-orient** after a break: what works, what is left, and how we work day to day.

---

## What we accomplished

| Area | Status | Notes |
|------|--------|--------|
| **Stage A** — car TCP :100, heartbeat, stock JSON motor protocol | Done (see `STAGE-A-STABLE-CAR-SERVICES.md`, Stage C docs) | ESP ↔ UNO path understood |
| **Stage B** — openpilot on macOS with **webcam/MJPEG** road cam | Done in tooling | `USE_WEBCAM=1`, `run_openpilot_manager_macos.sh`, ESP stream |
| **Stage C** — gated motor tests, motor suite | Done | `elegoo_motor_test_suite.py`, `scripts/stage-c-verify/` |
| **Stage D** — Python **bridge**: `SubMaster(sendcan)` → `PubMaster(can, pandaStates)` → TCP **N=4** `TORQUE_CMD` → ELEGOO | Done | [`elegoo_openpilot_bridge.py`](elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py), body `carstate` RX fix, [`artifacts/stage-d/STAGE-D-VERIFY.md`](artifacts/stage-d/STAGE-D-VERIFY.md) |
| **Stage E (control tuning)** — deadband, scale, bias, PWM clamp, smoothing, **stale sendcan** watchdog, **`--stale-sendcan-stop`** | Implemented + tested | [`elegoo_control_map.py`](elegoo-car-custom-tools/scripts/elegoo_control_map.py), CLI flags on bridge |
| **Sendcan diagnostics** — `sendcan_is_stale()`, integration tests, sanity shell script | Done | [`test_sendcan_stale_and_bridge.py`](scripts/stage-d-verify/test_sendcan_stale_and_bridge.py), `run_sendcan_bridge_sanity.sh` |
| **Automated verify** | Done | Pytest (Stage E + sendcan + Stage D) + plumbing smoke |

---

## What remains / known gaps

| Item | Owner | Notes |
|------|--------|--------|
| **Real `sendcan` from openpilot** when UI says “unavailable” | You + OP config | **`card`** must publish **`sendcan`** with **`TORQUE_CMD`**; bridge only passes through if messages exist. Use **`emit_torque_sendcan.py`** to prove the bridge path without full engagement. |
| **Full openpilot “green” on Mac** (model blobs, encoderd, loggerd, EKF) | Optional | **Not required** for motor bridge; noisy logs are expected. |
| **Stage E floor tuning** | You | Adjust `--torque-scale`, `--deadband`, `--bias-l/r`, `--pwm-min/max`, `--smooth-alpha`; add **`--stale-sendcan-stop`** if wheels creep at neutral. |
| **Stage F (if any)** | TBD | Not defined in repo; next features are your choice (e.g. logging, planner-in-loop). |

---

## Workflow (how we work on this repo)

1. **Always `cd` into the repo** before `./scripts/...` (paths are relative to repo root).
2. **Openpilot Python** uses **`openpilot/.venv`** — scripts that run bridge/tests `source` it via wrapper shells.
3. **Two common paths:**
   - **Software only:** run **`run_stage_e_verify.sh`** (or **`run_stage_d_verify.sh`**).
   - **Hardware + car:** **Terminal A** = manager; **Terminal B** = live bridge with **`CAR_IP`**.
4. **When debugging “no torque”:** run **`emit_torque_sendcan.py`** + bridge **dry-run**, or **`run_sendcan_bridge_sanity.sh`**, to separate **messaging** from **openpilot**.
5. **Docs:** stage-specific truth in **`artifacts/stage-*/`** and **`docs/`** under `elegoo-car-custom-tools`; strategy in **`STAGE-D-OPENPILOT-ELEGOO-BRIDGE.md`**.

---

## Exact commands (copy-paste)

Replace `CAR_IP` if your ESP32 is not `192.168.1.191`.

### One-time: make scripts executable

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
chmod +x scripts/stage-e-verify/run_stage_e_verify.sh \
  scripts/stage-d-verify/run_stage_d_verify.sh \
  scripts/stage-d-verify/run_stage_d_bridge.sh \
  scripts/stage-b-verify/run_openpilot_manager_macos.sh \
  scripts/stage-d-verify/run_sendcan_bridge_sanity.sh
```

### Full automated test suite (no car, needs `openpilot/.venv`)

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-e-verify/run_stage_e_verify.sh
```

**Look for:** `10 passed` (control), `5 passed` (sendcan), `8 passed` (bridge), plumbing line, then `Stage E automated verify: PASS`.

Alternate (includes same tests + order in Stage D script):

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-d-verify/run_stage_d_verify.sh
```

**Look for:** `Stage D automated verify: PASS` at the end.

### Sendcan path sanity (emitter + bridge dry-run, no openpilot)

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-d-verify/run_sendcan_bridge_sanity.sh
```

**Look for:** `dry-run` lines with **non-zero** `TORQUE_L` / `TORQUE_R` and `stale=False`, then `sendcan + bridge sanity: PASS`.

### Manual: synthetic `sendcan` only (two terminals)

**Terminal 1**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1/openpilot && source .venv/bin/activate
export PYTHONPATH="$PWD:$PWD/rednose_repo"
python3 ../scripts/stage-d-verify/emit_torque_sendcan.py
```

**Terminal 2**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
./scripts/stage-d-verify/run_stage_d_bridge.sh --mode dry-run --stale-sendcan-sec 0 --log-every-n 50
```

**Look for:** changing torque values in **`[dry-run]`** lines. **Ctrl+C** both when done.

### Live on hardware: openpilot + bridge (two terminals)

**Terminal A — openpilot manager + UI**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
export CAR_IP=192.168.1.191
./scripts/stage-b-verify/run_openpilot_manager_macos.sh
```

**Look for:** process list including **`webcamerad`**, **`ui`**, **`card`**; live camera in UI is OK even if overlay says “unavailable”.

**Terminal B — ELEGOO bridge (TCP port 100)**

```bash
cd /Users/lukekensik/coding/elegoo-comma-1
export CAR_IP=192.168.1.191
./scripts/stage-d-verify/run_stage_d_bridge.sh --mode live --tcp-host "$CAR_IP" \
  --tcp-send-hz 15 \
  --torque-scale 0.35 \
  --deadband 15 \
  --pwm-min 90 \
  --pwm-max 166 \
  --smooth-alpha 0.35 \
  --stale-sendcan-sec 0.5 \
  --control-log
```

**Look for:** **`[control]`** lines with **`ok`** (not only `stale_sendcan`); **`tl`/`tr`** non-zero when OP commands torque. If you only see **`stale_sendcan`** and **`tl=0`**, **`sendcan`** is not updating — fix OP/emitter path first.

**Optional — send firmware stop when stale instead of neutral N=4:**

Add **`--stale-sendcan-stop`** to the same command (helps if wheels creep).

**Stop:** **Ctrl+C** in Terminal B (bridge sends **`N=100`** stop), then **Ctrl+C** in Terminal A if you want to quit openpilot.

---

## Key file map

| Path | Role |
|------|------|
| [`elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py`](elegoo-car-custom-tools/scripts/elegoo_openpilot_bridge.py) | Main bridge |
| [`elegoo-car-custom-tools/scripts/elegoo_control_map.py`](elegoo-car-custom-tools/scripts/elegoo_control_map.py) | Torque→PWM + `sendcan_is_stale` |
| [`elegoo-car-custom-tools/scripts/elegoo_protocol.py`](elegoo-car-custom-tools/scripts/elegoo_protocol.py) | ELEGOO JSON (`N=4`, `N=100` stop) |
| [`scripts/stage-e-verify/README.md`](scripts/stage-e-verify/README.md) | Bridge usage + troubleshooting |
| [`scripts/stage-d-verify/README.md`](scripts/stage-d-verify/README.md) | Verify scripts index |
| [`artifacts/stage-d/STAGE-D-VERIFY.md`](artifacts/stage-d/STAGE-D-VERIFY.md) | Spec checklist + non-blockers |

---

## Updating this document

When you finish a milestone, edit the **Last updated** date and the **accomplished** / **remains** tables so the next session starts fast.
