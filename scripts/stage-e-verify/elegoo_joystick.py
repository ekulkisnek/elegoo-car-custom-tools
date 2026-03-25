#!/usr/bin/env python3
"""
Publish testJoystick for comma body / joystickd — keyboard-driven or constant.

joystickd maps:
  axes[0] → CC.actuators.accel  (× 4.0 → forward/back speed PID target)
  axes[1] → CC.actuators.torque (differential: positive = steer right)

Keyboard (when --keyboard):
  W / ↑  = forward         S / ↓  = backward
  A / ←  = pivot left      D / →  = pivot right
  E      = arc fwd-right   Q      = arc fwd-left
  Z      = arc back-left   C      = arc back-right
  SPACE  = stop (zero both axes)
  X      = quit

Without --keyboard, publishes a constant (--accel, --steer) pair.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_THIS = os.path.abspath(os.path.dirname(__file__))
_REPO = os.path.abspath(os.path.join(_THIS, "../.."))
_OP = os.environ.get("OPENPILOT_ROOT", os.path.join(_REPO, "openpilot"))
for _p in (_OP, os.path.join(_OP, "rednose_repo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cereal.messaging as messaging


def _publish_loop(pm: messaging.PubMaster, accel: float, steer: float, hz: float) -> None:
    interval = 1.0 / hz
    print(f"[joystick] constant accel={accel:.3f} steer={steer:.3f} @ {hz:.0f}Hz  (Ctrl+C to stop)", flush=True)
    while True:
        msg = messaging.new_message("testJoystick")
        msg.testJoystick.axes = [float(accel), float(steer)]
        msg.testJoystick.buttons = [False]
        pm.send("testJoystick", msg)
        time.sleep(interval)


def _keyboard_loop(pm: messaging.PubMaster, accel_max: float, steer_max: float, hz: float) -> None:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    interval = 1.0 / hz
    accel = 0.0
    steer = 0.0
    last_key_mono = time.monotonic()
    deadman_sec = 0.50

    print(f"[joystick] keyboard mode  accel_max={accel_max:.2f}  steer_max={steer_max:.2f}", flush=True)
    print("  W/↑=fwd  S/↓=back  A/←=pivot-L  D/→=pivot-R", flush=True)
    print("  Q=arc-fwd-left  E=arc-fwd-right", flush=True)
    print("  Z=arc-back-left  C=arc-back-right", flush=True)
    print("  SPACE=stop  X=quit", flush=True)

    try:
        tty.setcbreak(fd)
        while True:
            if select.select([sys.stdin], [], [], 0.0)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    seq = sys.stdin.read(2) if select.select([sys.stdin], [], [], 0.05)[0] else ""
                    if seq == "[A":
                        ch = "w"
                    elif seq == "[B":
                        ch = "s"
                    elif seq == "[C":
                        ch = "d"
                    elif seq == "[D":
                        ch = "a"
                ch = ch.lower()
                if ch == "x":
                    break
                elif ch == "w":
                    accel = accel_max
                    steer = 0.0
                elif ch == "s":
                    accel = -accel_max
                    steer = 0.0
                elif ch == "a":
                    steer = -steer_max
                    accel = 0.0
                elif ch == "d":
                    steer = steer_max
                    accel = 0.0
                elif ch == "e":
                    accel = accel_max
                    steer = steer_max
                elif ch == "q":
                    accel = accel_max
                    steer = -steer_max
                elif ch == "z":
                    accel = -accel_max
                    steer = -steer_max
                elif ch == "c":
                    accel = -accel_max
                    steer = steer_max
                elif ch == " ":
                    accel = 0.0
                    steer = 0.0
                last_key_mono = time.monotonic()

            if (time.monotonic() - last_key_mono) > deadman_sec:
                accel = 0.0
                steer = 0.0

            msg = messaging.new_message("testJoystick")
            msg.testJoystick.axes = [float(accel), float(steer)]
            msg.testJoystick.buttons = [False]
            pm.send("testJoystick", msg)
            time.sleep(interval)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        msg = messaging.new_message("testJoystick")
        msg.testJoystick.axes = [0.0, 0.0]
        msg.testJoystick.buttons = [False]
        pm.send("testJoystick", msg)
        print("\n[joystick] stopped (zero sent)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyboard", action="store_true", help="Interactive keyboard control (WASD + arrows)")
    ap.add_argument("--accel", type=float, default=0.15, help="Constant forward accel [-1..1] or keyboard max (default 0.15)")
    ap.add_argument("--steer", type=float, default=0.0, help="Constant steer [-1..1] (ignored in keyboard mode)")
    ap.add_argument("--steer-max", type=float, default=1.0, help="Keyboard max steer magnitude (default 1.0)")
    ap.add_argument("--hz", type=float, default=100.0, help="Publish rate (default 100)")
    args = ap.parse_args()

    pm = messaging.PubMaster(["testJoystick"])

    try:
        if args.keyboard:
            _keyboard_loop(pm, abs(args.accel), abs(args.steer_max), args.hz)
        else:
            _publish_loop(pm, args.accel, args.steer, args.hz)
    except KeyboardInterrupt:
        msg = messaging.new_message("testJoystick")
        msg.testJoystick.axes = [0.0, 0.0]
        msg.testJoystick.buttons = [False]
        pm.send("testJoystick", msg)
        print("\n[joystick] Ctrl+C — zero sent", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
