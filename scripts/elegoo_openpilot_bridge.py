#!/usr/bin/env python3
"""
ELEGOO ↔ openpilot bridge (Stage D/E): subscribe sendcan, publish can + pandaStates, TCP :100.

Modes:
  plumbing — D.1 synthetic can + pandaStates, no car TCP
  dry-run  — D.2 parse TORQUE_CMD, log mapped motor commands, no TCP
  live     — D.3 send per-motor N=1 commands to CAR_IP

Stage E: torque→speed tuning (deadband, scale, bias, smoothing, stale sendcan) via flags.

Requires openpilot on PYTHONPATH (see scripts/stage-d-verify/run_stage_d_bridge.sh).
"""
from __future__ import annotations

import argparse
import os
import select
import socket
import sys
import threading
import time
from typing import Any

# --- path bootstrap (repo root + openpilot + ELEGOO scripts) ---
_THIS = os.path.abspath(os.path.dirname(__file__))
_REPO = os.path.abspath(os.path.join(_THIS, "../.."))
_OP = os.environ.get("OPENPILOT_ROOT", os.path.join(_REPO, "openpilot"))
for _p in (_OP, os.path.join(_OP, "rednose_repo")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
if _THIS not in sys.path:
    sys.path.insert(0, _THIS)

import cereal.messaging as messaging  # noqa: E402
from cereal import car  # noqa: E402
from opendbc.can.packer import CANPacker  # noqa: E402
from opendbc.can.parser import CANParser  # noqa: E402
from openpilot.selfdrive.pandad import can_list_to_can_capnp  # noqa: E402

from elegoo_control_map import (  # noqa: E402
    DEFAULT_CONTROL_CONFIG,
    ControlConfig,
    SpeedSmoother,
    map_torque_to_speed_single,
    map_torques_to_speed_pair,
    sendcan_is_stale,
)
from elegoo_protocol import HEARTBEAT_FRAME, cmd_motor_pair, cmd_stop  # noqa: E402

DBC_NAME = "comma_body"
MAX_OP_TORQUE = 500
TORQUE_CMD_ADDR = 0x250  # 592 decimal, comma_body.dbc


def torque_to_speed(torque: float) -> int:
    """Map openpilot torque [-500, 500] to signed motor speed [-255, +255]."""
    return map_torque_to_speed_single(torque, DEFAULT_CONTROL_CONFIG)


def tcp_send_interval_sec(tcp_send_hz: float) -> float:
    """Minimum seconds between motor TCP sends when using rate limiting (not on-change)."""
    return 1.0 / max(float(tcp_send_hz), 1e-6)


def should_send_motor_tcp(
    now_mono: float,
    tcp_send_hz: float,
    tcp_send_on_change: bool,
    speed_l: int,
    speed_r: int,
    last_send_mono: float,
    last_sent_speed: tuple[int, int] | None,
) -> bool:
    """Whether to emit a motor command this tick (for testing and live loop)."""
    if tcp_send_on_change:
        if last_sent_speed is None:
            return True
        return (speed_l, speed_r) != last_sent_speed
    interval = tcp_send_interval_sec(tcp_send_hz)
    return (now_mono - last_send_mono) >= interval


def build_synthetic_can_msgs(
    packer: CANPacker,
    speed_l: float = 0.0,
    speed_r: float = 0.0,
    fault: bool = False,
) -> list[tuple[int, bytes, int]]:
    """RX frames for body CarState + CAN fingerprint (513, 514, 515, 516)."""
    msgs = []
    msgs.append(
        packer.make_can_msg(
            "MOTORS_DATA",
            0,
            {"SPEED_L": speed_l, "SPEED_R": speed_r},
        )
    )
    msgs.append(
        packer.make_can_msg(
            "VAR_VALUES",
            0,
            {
                "IGNITION": 1.0,
                "ENABLE_MOTORS": 0.0 if fault else 1.0,
                "FAULT": 1.0 if fault else 0.0,
                "MOTOR_ERR_L": 0.0,
                "MOTOR_ERR_R": 0.0,
            },
        )
    )
    msgs.append(
        packer.make_can_msg(
            "BODY_DATA",
            0,
            {
                "MCU_TEMP": 40.0,
                "BATT_VOLTAGE": 12.0,
                "BATT_PERCENTAGE": 80.0,
                "CHARGER_CONNECTED": 0.0,
            },
        )
    )
    msgs.append(
        packer.make_can_msg(
            "MOTORS_CURRENT",
            0,
            {
                "LEFT_PHA_AB": 0.0,
                "LEFT_PHA_BC": 0.0,
                "RIGHT_PHA_AB": 0.0,
                "RIGHT_PHA_BC": 0.0,
            },
        )
    )
    return [m for m in msgs if m[0] != 0]


def make_panda_states_msg(alternative_experience: int = 0) -> Any:
    dat = messaging.new_message("pandaStates", 1)
    dat.valid = True
    ps = dat.pandaStates[0]
    ps.ignitionLine = True
    ps.pandaType = "blackPanda"
    ps.controlsAllowed = True
    ps.safetyModel = car.CarParams.SafetyModel.body
    ps.safetyParam = 0
    ps.alternativeExperience = alternative_experience
    return dat


class TcpHeartbeatClient:
    """TCP client with background heartbeat echo; signals bridge on disconnect."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        connection_lost: threading.Event | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._connection_lost = connection_lost
        self.sock: socket.socket | None = None
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None

    def _signal_lost(self) -> None:
        if self._connection_lost is not None:
            self._connection_lost.set()

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.setblocking(False)
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()

    def close(self) -> None:
        self._stop.set()
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        if self._reader is not None:
            self._reader.join(timeout=1.5)
            self._reader = None
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def send_line(self, line: str) -> None:
        if self.sock is None:
            raise RuntimeError("not connected")
        try:
            self.sock.sendall(line.encode("utf-8"))
        except OSError:
            self._signal_lost()
            raise

    def _reader_loop(self) -> None:
        try:
            assert self.sock is not None
            buf = ""
            while not self._stop.is_set():
                ready, _, _ = select.select([self.sock], [], [], 0.2)
                if not ready:
                    continue
                try:
                    chunk = self.sock.recv(4096)
                except BlockingIOError:
                    continue
                except OSError:
                    self._signal_lost()
                    return
                if not chunk:
                    self._signal_lost()
                    return
                buf += chunk.decode("utf-8", errors="replace")
                while "}" in buf:
                    idx = buf.index("}") + 1
                    frame = buf[:idx]
                    buf = buf[idx:]
                    if frame == HEARTBEAT_FRAME:
                        try:
                            self.sock.sendall(HEARTBEAT_FRAME.encode("utf-8"))
                        except OSError:
                            self._signal_lost()
                            return
        except Exception:
            self._signal_lost()


class ElegooOpenpilotBridge:
    def __init__(
        self,
        mode: str,
        tcp_host: str | None,
        tcp_port: int,
        log_every_n: int,
        tcp_send_hz: float = 20.0,
        tcp_send_on_change: bool = False,
        control: ControlConfig | None = None,
        control_log: bool = False,
        stale_sendcan_stop: bool = False,
        feedback_alpha: float = 0.15,
    ) -> None:
        self.mode = mode
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.log_every_n = max(1, log_every_n)
        self.tcp_send_hz = float(tcp_send_hz)
        self.tcp_send_on_change = tcp_send_on_change
        self.control = control if control is not None else DEFAULT_CONTROL_CONFIG
        self.control_log = control_log
        self.stale_sendcan_stop = stale_sendcan_stop
        self.feedback_alpha = max(0.01, min(1.0, float(feedback_alpha)))
        self._smoother = SpeedSmoother(self.control.smooth_alpha)
        self.packer = CANPacker(DBC_NAME)
        self.torque_parser = CANParser(DBC_NAME, [("TORQUE_CMD", 100)], 0)
        self.sm = messaging.SubMaster(
            ["sendcan", "carParams"],
            ignore_alive=["carParams"],
        )
        self.pm = messaging.PubMaster(["can", "pandaStates"])
        self.tcp: TcpHeartbeatClient | None = None
        self._tcp_connection_lost = threading.Event()
        self._last_tcp_send_mono = -1e30
        self._last_sent_speed: tuple[int, int] | None = None
        self._tcp_send_fail_logged = False
        self._loop_count = 0
        self._last_tl = 0.0
        self._last_tr = 0.0
        self._last_sendcan_mono = time.monotonic()
        self._alt_exp = 0
        self._est_speed_l = 0.0
        self._est_speed_r = 0.0
        self._tcp_fault = False

    def _ensure_tcp(self) -> None:
        if self.mode != "live" or not self.tcp_host:
            return
        if self.tcp is not None and not self._tcp_connection_lost.is_set():
            return
        had_tcp = self.tcp is not None
        if self.tcp is not None:
            self.tcp.close()
            self.tcp = None
        self._tcp_connection_lost.clear()
        self._last_sent_speed = None
        self._last_tcp_send_mono = -1e30
        if had_tcp:
            print(f"[live] TCP reconnecting to {self.tcp_host}:{self.tcp_port} ...", flush=True)
        self.tcp = TcpHeartbeatClient(
            self.tcp_host,
            self.tcp_port,
            connection_lost=self._tcp_connection_lost,
        )
        self.tcp.connect()
        self._tcp_send_fail_logged = False
        if had_tcp:
            try:
                self.tcp.send_line(cmd_stop() + "\n")
            except OSError:
                pass
            self._smoother.reset()

    def _parse_torque(self, log_mono_time: int) -> tuple[float, float] | None:
        sc = self.sm["sendcan"]
        frames = [(c.address, c.dat, c.src) for c in sc]
        if not frames:
            return None
        self.torque_parser.update([(log_mono_time, frames)])
        vl = self.torque_parser.vl.get("TORQUE_CMD")
        if vl is None or "TORQUE_L" not in vl:
            return None
        return float(vl["TORQUE_L"]), float(vl["TORQUE_R"])

    def step(self) -> None:
        self.sm.update(0)
        if self.sm.updated["carParams"]:
            try:
                self._alt_exp = int(self.sm["carParams"].alternativeExperience)
            except Exception:
                self._alt_exp = 0

        if self.sm.updated["sendcan"]:
            self._last_sendcan_mono = time.monotonic()
            tmono = self.sm.logMonoTime["sendcan"]
            parsed = self._parse_torque(tmono)
            if parsed is not None:
                self._last_tl, self._last_tr = parsed

        tcp_fault = self._tcp_connection_lost.is_set() if self.mode == "live" else False
        self._tcp_fault = tcp_fault
        can_msgs = build_synthetic_can_msgs(
            self.packer,
            speed_l=self._est_speed_l,
            speed_r=self._est_speed_r,
            fault=tcp_fault,
        )
        self.pm.send("can", can_list_to_can_capnp(can_msgs, msgtype="can", valid=True))

        if self._loop_count % 20 == 0:
            self.pm.send("pandaStates", make_panda_states_msg(self._alt_exp))

        now = time.monotonic()
        stale = sendcan_is_stale(now, self._last_sendcan_mono, self.control.stale_sendcan_sec)

        raw_l, raw_r = map_torques_to_speed_pair(
            self._last_tl,
            self._last_tr,
            self.control,
            force_neutral=stale,
        )
        speed_l, speed_r = self._smoother.step(raw_l, raw_r)

        a = self.feedback_alpha
        self._est_speed_l = a * float(speed_l) + (1.0 - a) * self._est_speed_l
        self._est_speed_r = a * float(speed_r) + (1.0 - a) * self._est_speed_r

        motor_cmds = cmd_motor_pair(speed_l, speed_r)
        motor_line = "".join(c + "\n" for c in motor_cmds)
        stale_stop_line = cmd_stop() + "\n"

        self._loop_count += 1
        if self.control_log and self._loop_count % self.log_every_n == 0:
            reason = "stale_sendcan" if stale else "ok"
            print(
                f"[control] t={now:.3f} tl={self._last_tl:.2f} tr={self._last_tr:.2f} "
                f"raw=({raw_l},{raw_r}) spd=({speed_l},{speed_r}) {reason}",
                flush=True,
            )
        if self.mode == "dry-run" and self._loop_count % self.log_every_n == 0:
            print(
                f"[dry-run] TORQUE_L={self._last_tl:.1f} TORQUE_R={self._last_tr:.1f} "
                f"SPD_L={speed_l} SPD_R={speed_r} stale={stale} -> {motor_cmds}",
                flush=True,
            )

        if self.mode == "live":
            self._ensure_tcp()
            assert self.tcp is not None
            use_stale_stop = stale and self.stale_sendcan_stop
            if use_stale_stop:
                send_allowed = (now - self._last_tcp_send_mono) >= tcp_send_interval_sec(self.tcp_send_hz)
            else:
                send_allowed = should_send_motor_tcp(
                    now,
                    self.tcp_send_hz,
                    self.tcp_send_on_change,
                    speed_l,
                    speed_r,
                    self._last_tcp_send_mono,
                    self._last_sent_speed,
                )
            if send_allowed:
                line_out = stale_stop_line if use_stale_stop else motor_line
                try:
                    self.tcp.send_line(line_out)
                    self._last_tcp_send_mono = time.monotonic()
                    self._last_sent_speed = (speed_l, speed_r)
                except OSError as e:
                    if not self._tcp_send_fail_logged:
                        print(f"[live] TCP send failed: {e}", file=sys.stderr, flush=True)
                        self._tcp_send_fail_logged = True

        if self.mode == "plumbing" and self._loop_count == 1:
            print("[plumbing] publishing synthetic can + pandaStates (no TCP)", flush=True)

    def run(self, duration_sec: float | None) -> None:
        if self.mode == "live":
            if not self.tcp_host:
                raise SystemExit("live mode requires --tcp-host")
            print(
                f"[live] TCP {self.tcp_host}:{self.tcp_port} "
                f"(send_hz={self.tcp_send_hz}, on_change={self.tcp_send_on_change})",
                flush=True,
            )
        t0 = time.monotonic()
        try:
            while duration_sec is None or (time.monotonic() - t0) < duration_sec:
                self.step()
                time.sleep(0.01)
        finally:
            if self.tcp is not None:
                try:
                    self.tcp.send_line(cmd_stop() + "\n")
                except OSError:
                    pass
                self.tcp.close()
            self._smoother.reset()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--mode",
        choices=("plumbing", "dry-run", "live"),
        default="plumbing",
        help="D.1 plumbing | D.2 dry-run | D.3 live TCP",
    )
    ap.add_argument("--tcp-host", default=os.environ.get("CAR_IP") or os.environ.get("ELEGOO_HOST"))
    ap.add_argument("--tcp-port", type=int, default=100)
    ap.add_argument("--duration", type=float, default=None, help="Seconds then exit (default: run forever)")
    ap.add_argument("--log-every-n", type=int, default=100, help="dry-run: print every N loops (~100Hz)")
    ap.add_argument(
        "--tcp-send-hz",
        type=float,
        default=20.0,
        help="Max motor command rate to ESP when not using --tcp-send-on-change (default 20)",
    )
    ap.add_argument(
        "--tcp-send-on-change",
        action="store_true",
        help="Only send motor JSON when speed values change (reduces UART load)",
    )
    ap.add_argument(
        "--control-log",
        action="store_true",
        help="Log torque, raw speed, smoothed speed, stale reason (every --log-every-n loops)",
    )
    ap.add_argument("--deadband", type=float, default=0.0, help="Torque deadband (each axis); 0=off")
    ap.add_argument(
        "--torque-scale",
        type=float,
        default=1.0,
        help="Multiply torque after deadband (use <1 for conservative motion)",
    )
    ap.add_argument("--gain-l", type=float, default=1.0, help="Left torque gain")
    ap.add_argument("--gain-r", type=float, default=1.0, help="Right torque gain")
    ap.add_argument("--bias-l", type=int, default=0, help="Add to left speed after map")
    ap.add_argument("--bias-r", type=int, default=0, help="Add to right speed after map")
    ap.add_argument("--speed-max", type=int, default=255, help="Clamp absolute motor speed (0-255)")
    ap.add_argument(
        "--speed-min",
        type=int,
        default=0,
        help="Motor speed dead zone: |speed| below this becomes 0 (kills idle buzz)",
    )
    ap.add_argument(
        "--stale-sendcan-sec",
        type=float,
        default=0.0,
        help="If >0, force zero speed when no sendcan update for this long",
    )
    ap.add_argument(
        "--stale-sendcan-stop",
        action="store_true",
        help="In live mode, send firmware stop (N=100) when stale instead of per-motor stop",
    )
    ap.add_argument(
        "--smooth-alpha",
        type=float,
        default=1.0,
        help="Speed low-pass: 1=no smoothing, 0.2=heavy smoothing",
    )
    ap.add_argument(
        "--feedback-alpha",
        type=float,
        default=0.15,
        help="Synthetic speed feedback EMA alpha (0.01=slow, 1.0=instant; default 0.15)",
    )
    args = ap.parse_args()

    if args.mode == "live" and not args.tcp_host:
        print("error: set --tcp-host or CAR_IP for live mode", file=sys.stderr)
        return 2

    ctrl = ControlConfig(
        deadband=args.deadband,
        torque_scale=args.torque_scale,
        gain_l=args.gain_l,
        gain_r=args.gain_r,
        bias_l=args.bias_l,
        bias_r=args.bias_r,
        speed_max=args.speed_max,
        speed_min=args.speed_min,
        stale_sendcan_sec=args.stale_sendcan_sec,
        smooth_alpha=args.smooth_alpha,
    )

    bridge = ElegooOpenpilotBridge(
        mode=args.mode,
        tcp_host=args.tcp_host,
        tcp_port=args.tcp_port,
        log_every_n=args.log_every_n,
        tcp_send_hz=args.tcp_send_hz,
        tcp_send_on_change=args.tcp_send_on_change,
        control=ctrl,
        control_log=args.control_log,
        stale_sendcan_stop=args.stale_sendcan_stop,
        feedback_alpha=args.feedback_alpha,
    )
    bridge.run(args.duration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
