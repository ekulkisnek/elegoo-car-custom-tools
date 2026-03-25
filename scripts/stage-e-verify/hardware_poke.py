#!/usr/bin/env python3
"""
Minimal hardware poke tests for ELEGOO motor control.

Run with car on bench, wheels off ground. Each poke is a few seconds max.

Usage:
  python3 hardware_poke.py --host 192.168.1.191 --poke stop
  python3 hardware_poke.py --host 192.168.1.191 --poke n1_motors
  python3 hardware_poke.py --host 192.168.1.191 --poke n1_reverse
  python3 hardware_poke.py --host 192.168.1.191 --poke speed_sweep
  python3 hardware_poke.py --host 192.168.1.191 --poke differential_arcs
  python3 hardware_poke.py --host 192.168.1.191 --poke pivot_turns
  python3 hardware_poke.py --host 192.168.1.191 --poke all
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import time

_THIS = os.path.abspath(os.path.dirname(__file__))
_REPO = os.path.abspath(os.path.join(_THIS, "../.."))
_SCRIPTS = os.path.join(_REPO, "elegoo-car-custom-tools/scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from elegoo_protocol import (
    HEARTBEAT_FRAME,
    MotorDirection,
    MotorSelection,
    cmd_motor_control,
    cmd_motor_pair,
    cmd_stop,
)


def send_cmd(sock: socket.socket, cmd: str) -> None:
    sock.setblocking(True)
    sock.sendall((cmd + "\n").encode("utf-8"))
    sock.setblocking(False)


def drain_and_echo_heartbeats(sock: socket.socket) -> None:
    """Read any pending data from the socket, echo heartbeats back."""
    import select
    while select.select([sock], [], [], 0.0)[0]:
        try:
            data = sock.recv(4096)
        except (BlockingIOError, OSError):
            return
        if not data:
            return
        text = data.decode("utf-8", errors="replace")
        while HEARTBEAT_FRAME in text:
            try:
                sock.sendall(HEARTBEAT_FRAME.encode("utf-8"))
            except OSError:
                return
            text = text.replace(HEARTBEAT_FRAME, "", 1)


def sleep_with_heartbeat(sock: socket.socket, seconds: float, interval: float = 0.2) -> None:
    """Sleep for `seconds`, draining heartbeats every `interval`."""
    t0 = time.monotonic()
    while (time.monotonic() - t0) < seconds:
        drain_and_echo_heartbeats(sock)
        remaining = seconds - (time.monotonic() - t0)
        time.sleep(min(interval, max(remaining, 0)))


def connect(host: str, port: int) -> socket.socket:
    print(f"  Connecting to {host}:{port}...", flush=True)
    sock = socket.create_connection((host, port), timeout=5.0)
    sock.setblocking(False)
    print(f"  Connected.", flush=True)
    return sock


def poke_stop(host: str, port: int) -> None:
    """Poke 1: TCP connect + N=100 stop. No motion expected."""
    print("\n=== POKE 1: Stop Baseline ===")
    print("  Sending N=100 (stop) only.")
    print("  >>> WATCH THE WHEELS — they should NOT move. <<<\n")

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        time.sleep(2.0)
        send_cmd(sock, cmd_stop())
        time.sleep(0.5)
    finally:
        try:
            sock.close()
        except OSError:
            pass

    print("  Done. Wheels should not have moved.")


def poke_n1_motors(host: str, port: int) -> None:
    """Poke 2: N=1 per-motor test — left motor only, then right motor only."""
    print("\n=== POKE 2: N=1 Per-Motor Identification ===")
    print("  Burst 1: LEFT_B motor forward at speed 80 for 2s.")
    print("  >>> WATCH: Only ONE wheel should spin. Which side? <<<\n")

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        time.sleep(0.5)

        print("  >>> BURST 1 — LEFT_B forward speed=80 <<<", flush=True)
        send_cmd(sock, cmd_motor_control(MotorSelection.LEFT_B, MotorDirection.FORWARD, 80))
        time.sleep(2.0)
        print("  >>> STOPPING <<<", flush=True)
        send_cmd(sock, cmd_stop())
        time.sleep(3.0)

        print("  Burst 2: RIGHT_A motor forward at speed 80 for 2s.")
        print("  >>> WATCH: The OTHER wheel should spin now. <<<\n")
        print("  >>> BURST 2 — RIGHT_A forward speed=80 <<<", flush=True)
        send_cmd(sock, cmd_motor_control(MotorSelection.RIGHT_A, MotorDirection.FORWARD, 80))
        time.sleep(2.0)
        print("  >>> STOPPING <<<", flush=True)
        send_cmd(sock, cmd_stop())
        time.sleep(0.5)
    finally:
        try:
            sock.close()
        except OSError:
            pass

    print("\n  Done.")
    print("  Expected: Burst 1 = left wheel only, Burst 2 = right wheel only.")
    print("  If swapped: LEFT_B and RIGHT_A labels are reversed in firmware.")


def poke_n1_reverse(host: str, port: int) -> None:
    """Poke 3: N=1 reverse direction — both motors backward."""
    print("\n=== POKE 3: N=1 Reverse Direction ===")
    print("  Sending both motors BACKWARD at speed 80 for 2s via cmd_motor_pair(-80, -80).")
    print("  >>> WATCH: Both wheels should spin BACKWARD. <<<\n")

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        time.sleep(0.5)

        cmds = cmd_motor_pair(-80, -80)
        print(f"  >>> MOTORS ON NOW — reverse speed=80 <<<", flush=True)
        for cmd in cmds:
            send_cmd(sock, cmd)
        time.sleep(2.0)
        print("  >>> STOPPING <<<", flush=True)
        send_cmd(sock, cmd_stop())
        time.sleep(0.5)
    finally:
        try:
            sock.close()
        except OSError:
            pass

    print("\n  Done.")
    print("  Expected: Both wheels spin backward (opposite to Poke 2 forward).")


def poke_speed_sweep(host: str, port: int) -> None:
    """Poke 4: N=4 forward at increasing speeds to find motor stall threshold."""
    speeds = [10, 20, 30, 40, 50, 60, 80]
    print("\n=== POKE 4: Speed Sweep (find motor stall threshold) ===")
    print(f"  Will test N=4 forward at speeds: {speeds}")
    print("  Each speed runs for 2s with a 1s stop between.")
    print("  >>> WATCH: Note the FIRST speed where wheels visibly move. <<<\n")

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        sleep_with_heartbeat(sock, 0.5)

        for spd in speeds:
            cmds = cmd_motor_pair(spd, spd)
            print(f"  >>> speed={spd:3d}/255 ({spd*100//255:2d}% duty) — WATCHING... <<<", flush=True)
            for cmd in cmds:
                send_cmd(sock, cmd)
            sleep_with_heartbeat(sock, 2.0)
            print(f"  >>> STOP <<<", flush=True)
            send_cmd(sock, cmd_stop())
            sleep_with_heartbeat(sock, 1.0)
    finally:
        try:
            send_cmd(sock, cmd_stop())
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    print("\n  Done. What was the FIRST speed where wheels moved?")
    print("  Use that value as the motor stall threshold for tuning.")


def poke_differential_arcs(host: str, port: int) -> None:
    """Poke 5: N=4 differential arcs — one side faster than the other."""
    print("\n=== POKE 5: Differential Arc Turns (N=4) ===")
    print("  Tests arcing by running both motors forward at different speeds.")
    print("  The car should arc toward the SLOWER side.\n")

    tests = [
        ("Arc RIGHT (D1=20, D2=50)", 20, 50, "slow right wheel, fast left → arc right"),
        ("Arc LEFT  (D1=50, D2=20)", 50, 20, "fast right wheel, slow left → arc left"),
        ("Wide arc RIGHT (D1=30, D2=50)", 30, 50, "gentle right arc"),
        ("Tight arc RIGHT (D1=10, D2=50)", 10, 50, "tight right arc"),
    ]

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        sleep_with_heartbeat(sock, 0.5)

        for label, sl, sr, desc in tests:
            cmds = cmd_motor_pair(sl, sr)
            print(f"  >>> {label} — {desc} <<<", flush=True)
            for cmd in cmds:
                send_cmd(sock, cmd)
            sleep_with_heartbeat(sock, 2.5)
            print(f"  >>> STOP <<<", flush=True)
            send_cmd(sock, cmd_stop())
            sleep_with_heartbeat(sock, 1.5)
    finally:
        try:
            send_cmd(sock, cmd_stop())
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    print("\n  Done.")
    print("  Expected: Car arcs toward the slower wheel side.")
    print("  If no arc: the speed difference may be too small for traction.")


def poke_pivot_turns(host: str, port: int) -> None:
    """Poke 6: N=3 pivot turns — one side forward, other backward."""
    print("\n=== POKE 6: Pivot Turns (N=3) ===")
    print("  Tests tank-style pivoting via cmd_motor_pair with opposite signs.\n")

    tests = [
        ("Pivot RIGHT (sl=-40, sr=40)", -40, 40, "right wheel back, left forward → pivot right"),
        ("Pivot LEFT  (sl=40, sr=-40)", 40, -40, "right wheel forward, left back → pivot left"),
    ]

    sock = connect(host, port)
    try:
        send_cmd(sock, cmd_stop())
        sleep_with_heartbeat(sock, 0.5)

        for label, sl, sr, desc in tests:
            cmds = cmd_motor_pair(sl, sr)
            print(f"  >>> {label} — {desc} <<<", flush=True)
            for cmd in cmds:
                send_cmd(sock, cmd)
            sleep_with_heartbeat(sock, 2.0)
            print(f"  >>> STOP <<<", flush=True)
            send_cmd(sock, cmd_stop())
            sleep_with_heartbeat(sock, 1.5)
    finally:
        try:
            send_cmd(sock, cmd_stop())
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    print("\n  Done.")
    print("  Expected: Car pivots in place (opposite wheel directions).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=os.environ.get("CAR_IP", "192.168.1.191"))
    ap.add_argument("--port", type=int, default=100)
    ap.add_argument("--poke", choices=[
        "stop", "n1_motors", "n1_reverse", "speed_sweep",
        "differential_arcs", "pivot_turns", "all",
    ], required=True)
    args = ap.parse_args()

    if args.poke == "stop":
        poke_stop(args.host, args.port)
    elif args.poke == "n1_motors":
        poke_n1_motors(args.host, args.port)
    elif args.poke == "n1_reverse":
        poke_n1_reverse(args.host, args.port)
    elif args.poke == "speed_sweep":
        poke_speed_sweep(args.host, args.port)
    elif args.poke == "differential_arcs":
        poke_differential_arcs(args.host, args.port)
    elif args.poke == "pivot_turns":
        poke_pivot_turns(args.host, args.port)
    elif args.poke == "all":
        poke_stop(args.host, args.port)
        time.sleep(2.0)
        poke_n1_motors(args.host, args.port)
        time.sleep(2.0)
        poke_n1_reverse(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
