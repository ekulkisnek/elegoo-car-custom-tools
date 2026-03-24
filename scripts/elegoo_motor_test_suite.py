#!/usr/bin/env python3
"""Guided motor-control tests for the stock ELEGOO TCP bridge on port 100."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import select
import socket
import sys
import threading
import time
from typing import Callable

from elegoo_protocol import (
    DEFAULT_PORT,
    EXPECTATIONS,
    HEARTBEAT_FRAME,
    Direction,
    MotorDirection,
    MotorSelection,
    RockerDirection,
    cmd_car_untimed,
    cmd_motor_control,
    cmd_motor_speed,
    cmd_rocker,
    cmd_stop,
)


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = ROOT / "output" / "motor-tests"


@dataclass(frozen=True)
class TestStep:
    key: str
    title: str
    command_factory: Callable[[], str]
    settle_seconds: float
    expected_key: str
    safety_note: str


SAFE_SPEED = 80
ARC_FAST = 100
ARC_SLOW = 45


TEST_STEPS: list[TestStep] = [
    TestStep(
        key="stop_baseline",
        title="Baseline stop",
        command_factory=cmd_stop,
        settle_seconds=1.0,
        expected_key="stop",
        safety_note="Use this before and after every movement block.",
    ),
    # N=2 timed linear (APP) can fail on some bridges while N=3 untimed works; Stage C uses N=3 for forward/back.
    TestStep(
        key="untimed_forward",
        title="Untimed forward (then stop after prompt)",
        command_factory=lambda: cmd_car_untimed(Direction.FORWARD, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="car_forward",
        safety_note="Same opcode family as turns (N=3). Runner sends stop after your observation.",
    ),
    TestStep(
        key="untimed_backward",
        title="Untimed backward (then stop after prompt)",
        command_factory=lambda: cmd_car_untimed(Direction.BACKWARD, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="car_backward",
        safety_note="Keep clear behind the car. Runner sends stop after your observation.",
    ),
    TestStep(
        key="untimed_left",
        title="Untimed left turn with manual stop",
        command_factory=lambda: cmd_car_untimed(Direction.LEFT, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="car_left",
        safety_note="Runner sends a stop after the observation prompt.",
    ),
    TestStep(
        key="untimed_right",
        title="Untimed right turn with manual stop",
        command_factory=lambda: cmd_car_untimed(Direction.RIGHT, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="car_right",
        safety_note="Runner sends a stop after the observation prompt.",
    ),
    TestStep(
        key="rocker_left_forward",
        title="Rocker diagonal left-forward",
        command_factory=lambda: cmd_rocker(RockerDirection.LEFT_FORWARD),
        settle_seconds=1.0,
        expected_key="rocker_left_forward",
        safety_note="Runner sends rocker stop and standby afterward.",
    ),
    TestStep(
        key="rocker_right_forward",
        title="Rocker diagonal right-forward",
        command_factory=lambda: cmd_rocker(RockerDirection.RIGHT_FORWARD),
        settle_seconds=1.0,
        expected_key="rocker_right_forward",
        safety_note="Runner sends rocker stop and standby afterward.",
    ),
    TestStep(
        key="single_right_motor",
        title="Single right motor forward",
        command_factory=lambda: cmd_motor_control(MotorSelection.RIGHT_A, MotorDirection.FORWARD, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="single_right_forward",
        safety_note="This isolates motor A, labeled Right in driver comments.",
    ),
    TestStep(
        key="single_left_motor",
        title="Single left motor forward",
        command_factory=lambda: cmd_motor_control(MotorSelection.LEFT_B, MotorDirection.FORWARD, SAFE_SPEED),
        settle_seconds=1.0,
        expected_key="single_left_forward",
        safety_note="This isolates motor B, labeled Left in driver comments.",
    ),
    TestStep(
        key="differential_arc",
        title="Differential forward arc",
        command_factory=lambda: cmd_motor_speed(ARC_SLOW, ARC_FAST),
        settle_seconds=1.0,
        expected_key="differential_forward_left_bias",
        safety_note="Both motors forward, unequal PWM.",
    ),
]


class BridgeClient:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.rx_log: list[dict[str, object]] = []

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.setblocking(False)
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def send(self, frame: str) -> None:
        if self.sock is None:
            raise RuntimeError("BridgeClient is not connected")
        self.sock.sendall(frame.encode("utf-8"))

    def _reader_loop(self) -> None:
        assert self.sock is not None
        buf = ""
        while not self.stop_event.is_set():
            ready, _, _ = select.select([self.sock], [], [], 0.2)
            if not ready:
                continue
            try:
                chunk = self.sock.recv(4096)
            except BlockingIOError:
                continue
            if not chunk:
                return
            buf += chunk.decode("utf-8", errors="replace")
            while "}" in buf:
                idx = buf.index("}") + 1
                frame = buf[:idx]
                buf = buf[idx:]
                ts = datetime.now(timezone.utc).isoformat()
                self.rx_log.append({"ts": ts, "frame": frame})
                if frame == HEARTBEAT_FRAME:
                    try:
                        self.send(HEARTBEAT_FRAME)
                    except OSError:
                        return


def prompt_result(step: TestStep) -> str:
    expectation = EXPECTATIONS[step.expected_key]
    print()
    print(f"Expected: {expectation.expected_vehicle_motion}")
    print(f"Firmware basis: {expectation.firmware_basis}")
    print(f"Safety note: {step.safety_note}")
    print("Observation options: y = matched, n = did not match, s = skip, q = abort")
    while True:
        answer = input("What did you observe? [y/n/s/q]: ").strip().lower()
        if answer in {"y", "n", "s", "q"}:
            return answer


def make_log_path(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return log_dir / f"motor-test-session_{stamp}.json"


def run_suite(args: argparse.Namespace) -> int:
    log_path = make_log_path(args.log_dir)
    results: list[dict[str, object]] = []
    client: BridgeClient | None = None

    if not args.dry_run:
        client = BridgeClient(args.host, args.port, args.timeout)
        client.connect()

    try:
        for step in TEST_STEPS:
            command = step.command_factory()
            expectation = EXPECTATIONS[step.expected_key]
            ts = datetime.now(timezone.utc).isoformat()
            print()
            print(f"== {step.title} ==")
            print(f"Command: {command}")
            print(f"Expected motion: {expectation.expected_vehicle_motion}")

            if not args.dry_run:
                assert client is not None
                client.send(command)
                time.sleep(step.settle_seconds)

            if args.non_interactive:
                verdict = "sent"
            else:
                verdict = prompt_result(step)
                if verdict == "q":
                    results.append({"ts": ts, "step": step.key, "command": command, "result": "aborted"})
                    break

            results.append(
                {
                    "ts": ts,
                    "step": step.key,
                    "title": step.title,
                    "command": command,
                    "expected_key": step.expected_key,
                    "expected_motion": expectation.expected_vehicle_motion,
                    "result": verdict,
                }
            )

            if step.key.startswith("untimed_") or step.key.startswith("single_") or step.key in {"differential_arc"}:
                if not args.dry_run:
                    client.send(cmd_stop())
                    time.sleep(0.4)

            if step.key.startswith("rocker_"):
                if not args.dry_run:
                    client.send(cmd_rocker(RockerDirection.STOP))
                    time.sleep(0.2)
                    client.send(cmd_stop())
                    time.sleep(0.4)

        if not args.dry_run and client is not None:
            client.send(cmd_stop())
            time.sleep(0.2)
    finally:
        rx_log = client.rx_log if client is not None else []
        if client is not None:
            client.close()

        payload = {
            "host": args.host,
            "port": args.port,
            "dry_run": args.dry_run,
            "results": results,
            "rx_frames": rx_log,
        }
        log_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print()
        print(f"Wrote session log: {log_path}")
        if rx_log:
            print(f"Captured {len(rx_log)} inbound frame(s).")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("ELEGOO_HOST", "192.168.4.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ELEGOO_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true", help="Do not connect; print and log the planned commands only.")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt for observer verdicts.")
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    return parser


def main() -> int:
    return run_suite(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
