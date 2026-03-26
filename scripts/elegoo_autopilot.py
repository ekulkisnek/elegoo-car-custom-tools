#!/usr/bin/env python3
"""
Autopilot for ELEGOO: reads openpilot's modelV2 and publishes testJoystick.

The driving model produces desiredCurvature and desiredAcceleration.
This script maps those to testJoystick axes that joystickd converts
into carControl for the body carcontroller PID pipeline.

joystickd mapping:
  axes[0] -> CC.actuators.accel  (x4.0 -> speed PID target)
  axes[1] -> CC.actuators.torque (differential steering)
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

_THIS = os.path.abspath(os.path.dirname(__file__))
_REPO = os.path.abspath(os.path.join(_THIS, "../.."))
_OP = os.environ.get("OPENPILOT_ROOT", os.path.join(_REPO, "openpilot"))
for _p in (_OP, os.path.join(_OP, "rednose_repo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import cereal.messaging as messaging


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def autopilot_loop(
    accel_scale: float,
    curv_scale: float,
    max_accel: float,
    max_steer: float,
    hz: float,
    log_hz: float,
) -> None:
    sm = messaging.SubMaster(["modelV2"], frequency=hz)
    pm = messaging.PubMaster(["testJoystick"])

    interval = 1.0 / hz
    log_interval = 1.0 / max(0.1, log_hz)
    last_log = 0.0
    model_frames = 0
    stale_count = 0

    print(
        f"[autopilot] accel_scale={accel_scale:.2f}  curv_scale={curv_scale:.2f}  "
        f"max_accel={max_accel:.2f}  max_steer={max_steer:.2f}  hz={hz:.0f}",
        flush=True,
    )
    print("[autopilot] waiting for modelV2...", flush=True)

    while True:
        sm.update(0)

        accel_axis = 0.0
        steer_axis = 0.0

        if sm.updated["modelV2"]:
            mv2 = sm["modelV2"]
            action = mv2.action

            if action.shouldStop:
                accel_axis = 0.0
                steer_axis = 0.0
            else:
                raw_accel = action.desiredAcceleration
                raw_curv = action.desiredCurvature

                accel_axis = _clamp(raw_accel / accel_scale, -1.0, 1.0)
                steer_axis = _clamp(raw_curv / curv_scale, -1.0, 1.0)

                accel_axis = _clamp(accel_axis, -max_accel, max_accel)
                steer_axis = _clamp(steer_axis, -max_steer, max_steer)

            model_frames += 1
            stale_count = 0

            now = time.monotonic()
            if now - last_log >= log_interval:
                conf = str(mv2.confidence) if hasattr(mv2, "confidence") else "n/a"
                print(
                    f"[autopilot] frame={model_frames}  accel={accel_axis:+.3f}  "
                    f"steer={steer_axis:+.3f}  raw_a={action.desiredAcceleration:+.3f}  "
                    f"raw_c={action.desiredCurvature:+.4f}  stop={action.shouldStop}  "
                    f"conf={conf}",
                    flush=True,
                )
                last_log = now
        else:
            stale_count += 1
            if stale_count == int(hz * 2) and model_frames == 0:
                print("[autopilot] still waiting for modelV2...", flush=True)
                stale_count = 0

        msg = messaging.new_message("testJoystick")
        msg.testJoystick.axes = [float(accel_axis), float(steer_axis)]
        msg.testJoystick.buttons = [False]
        pm.send("testJoystick", msg)

        time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--accel-scale", type=float, default=2.0,
        help="Model desiredAcceleration value that maps to axes[0]=1.0 (default 2.0 m/s^2)",
    )
    ap.add_argument(
        "--curv-scale", type=float, default=0.3,
        help="Model desiredCurvature value that maps to axes[1]=1.0 (default 0.3 1/m)",
    )
    ap.add_argument(
        "--max-accel", type=float, default=0.3,
        help="Clamp accel axis magnitude (default 0.3 = 30%% throttle)",
    )
    ap.add_argument(
        "--max-steer", type=float, default=0.8,
        help="Clamp steer axis magnitude (default 0.8)",
    )
    ap.add_argument(
        "--hz", type=float, default=20.0,
        help="Publish rate in Hz (default 20, matches model output rate)",
    )
    ap.add_argument(
        "--log-hz", type=float, default=1.0,
        help="Log print rate in Hz (default 1.0)",
    )
    args = ap.parse_args()

    def _sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _sigterm)

    try:
        autopilot_loop(
            accel_scale=args.accel_scale,
            curv_scale=args.curv_scale,
            max_accel=args.max_accel,
            max_steer=args.max_steer,
            hz=args.hz,
            log_hz=args.log_hz,
        )
    except KeyboardInterrupt:
        pass

    pm = messaging.PubMaster(["testJoystick"])
    msg = messaging.new_message("testJoystick")
    msg.testJoystick.axes = [0.0, 0.0]
    msg.testJoystick.buttons = [False]
    pm.send("testJoystick", msg)
    print("\n[autopilot] stopped (zero sent)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
