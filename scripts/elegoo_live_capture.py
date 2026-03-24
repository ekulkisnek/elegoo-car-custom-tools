#!/usr/bin/env python3
"""Continuously capture live ELEGOO serial and network streams."""

from __future__ import annotations

import argparse
import codecs
import http.client
import os
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, TextIO

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    serial = None


HEARTBEAT_FRAME = "{Heartbeat}"
SERIAL_RETRY_SECONDS = 2.0
NETWORK_RETRY_SECONDS = 2.0
STREAM_READ_SIZE = 4096


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_name() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class LogWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, message: str) -> None:
        with self._lock:
            self._fh.write(message)
            self._fh.flush()

    def line(self, message: str) -> None:
        self.write(f"[{utc_stamp()}] {message}\n")

    def close(self) -> None:
        with self._lock:
            self._fh.close()


class BinaryWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("ab")
        self._lock = threading.Lock()

    def write(self, data: bytes) -> None:
        with self._lock:
            self._fh.write(data)
            self._fh.flush()

    def close(self) -> None:
        with self._lock:
            self._fh.close()


def append_decoded_lines(
    decoder: codecs.IncrementalDecoder,
    text_buffer: str,
    chunk: bytes,
    text_log: LogWriter,
) -> str:
    text_buffer += decoder.decode(chunk)
    while True:
        newline = text_buffer.find("\n")
        if newline < 0:
            break
        line = text_buffer[:newline].rstrip("\r")
        text_log.line(line)
        text_buffer = text_buffer[newline + 1 :]
    return text_buffer


class SerialCapture(threading.Thread):
    def __init__(self, name: str, port: str, baud: int, out_dir: Path, stop_event: threading.Event) -> None:
        super().__init__(name=name, daemon=True)
        self.port = port
        self.baud = baud
        self.stop_event = stop_event
        self.text_log = LogWriter(out_dir / f"{name}.log")
        self.raw_log = BinaryWriter(out_dir / f"{name}.raw")

    def run(self) -> None:
        if serial is None:
            self.text_log.line("pyserial not installed; skipping serial capture.")
            return

        while not self.stop_event.is_set():
            try:
                self.text_log.line(f"opening port={self.port} baud={self.baud}")
                with serial.Serial(self.port, self.baud, timeout=0.25) as ser:
                    try:
                        ser.reset_input_buffer()
                    except Exception:
                        pass
                    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                    text_buffer = ""
                    while not self.stop_event.is_set():
                        chunk = ser.read(STREAM_READ_SIZE)
                        if not chunk:
                            continue
                        self.raw_log.write(chunk)
                        text_buffer = append_decoded_lines(decoder, text_buffer, chunk, self.text_log)
                    if text_buffer:
                        self.text_log.line(text_buffer.rstrip("\r"))
            except Exception as exc:
                self.text_log.line(f"serial error: {exc}")
                self.stop_event.wait(SERIAL_RETRY_SECONDS)

    def close(self) -> None:
        self.text_log.close()
        self.raw_log.close()


class TCPBridgeCapture(threading.Thread):
    def __init__(self, host: str, port: int, out_dir: Path, stop_event: threading.Event) -> None:
        super().__init__(name="tcp_bridge", daemon=True)
        self.host = host
        self.port = port
        self.stop_event = stop_event
        self.log = LogWriter(out_dir / "tcp_bridge.log")
        self.raw = BinaryWriter(out_dir / "tcp_bridge.raw")

    def run(self) -> None:
        while not self.stop_event.is_set():
            sock: socket.socket | None = None
            try:
                self.log.line(f"connecting to {self.host}:{self.port}")
                sock = socket.create_connection((self.host, self.port), timeout=5)
                sock.settimeout(1.0)
                self.log.line("connected")
                buffer = ""
                while not self.stop_event.is_set():
                    try:
                        data = sock.recv(STREAM_READ_SIZE)
                    except socket.timeout:
                        continue
                    if not data:
                        raise ConnectionError("remote closed connection")
                    self.raw.write(data)
                    buffer += data.decode("utf-8", errors="replace")
                    while True:
                        start = buffer.find("{")
                        if start < 0:
                            buffer = ""
                            break
                        end = buffer.find("}", start)
                        if end < 0:
                            if start > 0:
                                buffer = buffer[start:]
                            break
                        frame = buffer[start : end + 1]
                        self.log.line(f"rx {frame}")
                        if frame == HEARTBEAT_FRAME:
                            sock.sendall(HEARTBEAT_FRAME.encode("utf-8"))
                            self.log.line("tx {Heartbeat}")
                        buffer = buffer[end + 1 :]
            except Exception as exc:
                self.log.line(f"tcp error: {exc}")
                self.stop_event.wait(NETWORK_RETRY_SECONDS)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass

    def close(self) -> None:
        self.log.close()
        self.raw.close()


class StatusPollCapture(threading.Thread):
    def __init__(self, host: str, port: int, interval: float, out_dir: Path, stop_event: threading.Event) -> None:
        super().__init__(name="http_status", daemon=True)
        self.host = host
        self.port = port
        self.interval = interval
        self.stop_event = stop_event
        self.log = LogWriter(out_dir / "http_status.log")

    def run(self) -> None:
        while not self.stop_event.is_set():
            conn: http.client.HTTPConnection | None = None
            try:
                conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
                conn.request("GET", "/status")
                resp = conn.getresponse()
                body = resp.read().decode("utf-8", errors="replace")
                self.log.line(f"status={resp.status} body={body}")
            except Exception as exc:
                self.log.line(f"http status error: {exc}")
            finally:
                if conn is not None:
                    conn.close()
            self.stop_event.wait(self.interval)

    def close(self) -> None:
        self.log.close()


class StreamCapture(threading.Thread):
    def __init__(
        self,
        host: str,
        port: int,
        save_raw: bool,
        stats_interval: float,
        out_dir: Path,
        stop_event: threading.Event,
    ) -> None:
        super().__init__(name="http_stream", daemon=True)
        self.host = host
        self.port = port
        self.save_raw = save_raw
        self.stats_interval = stats_interval
        self.stop_event = stop_event
        self.log = LogWriter(out_dir / "http_stream.log")
        self.raw = BinaryWriter(out_dir / "http_stream.mjpeg") if save_raw else None

    def run(self) -> None:
        marker = b"Content-Type: image/jpeg"
        while not self.stop_event.is_set():
            conn: http.client.HTTPConnection | None = None
            try:
                self.log.line(f"connecting to http://{self.host}:{self.port}/stream")
                conn = http.client.HTTPConnection(self.host, self.port, timeout=10)
                conn.request("GET", "/stream")
                resp = conn.getresponse()
                self.log.line(f"stream status={resp.status} reason={resp.reason}")
                if resp.status != 200:
                    raise RuntimeError(f"unexpected status {resp.status}")

                total_bytes = 0
                interval_bytes = 0
                interval_frames = 0
                leftover = b""
                next_log = time.monotonic() + self.stats_interval
                while not self.stop_event.is_set():
                    chunk = resp.read(STREAM_READ_SIZE)
                    if not chunk:
                        raise ConnectionError("stream ended")
                    if self.raw is not None:
                        self.raw.write(chunk)
                    total_bytes += len(chunk)
                    interval_bytes += len(chunk)
                    combined = leftover + chunk
                    interval_frames += combined.count(marker)
                    leftover = combined[-len(marker) + 1 :] if len(combined) >= len(marker) else combined
                    now = time.monotonic()
                    if now >= next_log:
                        self.log.line(
                            f"bytes_total={total_bytes} bytes_interval={interval_bytes} jpeg_headers_interval={interval_frames}"
                        )
                        interval_bytes = 0
                        interval_frames = 0
                        next_log = now + self.stats_interval
            except Exception as exc:
                self.log.line(f"http stream error: {exc}")
                self.stop_event.wait(NETWORK_RETRY_SECONDS)
            finally:
                if conn is not None:
                    conn.close()

    def close(self) -> None:
        self.log.close()
        if self.raw is not None:
            self.raw.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("ELEGOO_HOST"), help="ESP32 host or IP for HTTP/TCP capture")
    parser.add_argument("--esp-port", default="/dev/cu.usbmodem21201", help="ESP32 USB serial device")
    parser.add_argument("--uno-port", default="/dev/cu.usbserial-3120", help="UNO USB serial device")
    parser.add_argument("--esp-baud", type=int, default=115200, help="ESP32 serial baud")
    parser.add_argument("--uno-baud", type=int, default=115200, help="UNO serial baud")
    parser.add_argument("--tcp-port", type=int, default=100, help="ESP32 TCP bridge port")
    parser.add_argument("--http-port", type=int, default=80, help="ESP32 HTTP status port")
    parser.add_argument("--stream-port", type=int, default=81, help="ESP32 MJPEG stream port")
    parser.add_argument("--status-interval", type=float, default=2.0, help="Seconds between /status polls")
    parser.add_argument("--stream-stats-interval", type=float, default=2.0, help="Seconds between /stream stats lines")
    parser.add_argument(
        "--out-dir",
        default=str(Path("output") / "live-capture" / session_name()),
        help="Directory for capture logs",
    )
    parser.add_argument("--no-esp-serial", action="store_true", help="Disable ESP32 serial capture")
    parser.add_argument("--no-uno-serial", action="store_true", help="Disable UNO serial capture")
    parser.add_argument("--no-tcp", action="store_true", help="Disable TCP bridge capture")
    parser.add_argument("--no-http-status", action="store_true", help="Disable HTTP /status polling")
    parser.add_argument("--no-http-stream", action="store_true", help="Disable HTTP /stream capture")
    parser.add_argument("--save-mjpeg", action="store_true", help="Persist raw /stream bytes to http_stream.mjpeg")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.no_tcp or not args.no_http_status or not args.no_http_stream:
        if not args.host:
            parser.error("--host is required unless all network captures are disabled")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = LogWriter(out_dir / "session.log")
    summary.line(f"output_dir={out_dir}")
    summary.line(
        "serial_enabled="
        f"esp={not args.no_esp_serial} uno={not args.no_uno_serial} "
        f"network_enabled=tcp={not args.no_tcp} status={not args.no_http_status} stream={not args.no_http_stream}"
    )
    if args.host:
        summary.line(
            f"host={args.host} tcp_port={args.tcp_port} http_port={args.http_port} stream_port={args.stream_port}"
        )

    stop_event = threading.Event()
    workers: list[threading.Thread] = []
    closers: list[object] = []

    if not args.no_esp_serial:
        worker = SerialCapture("esp32_serial", args.esp_port, args.esp_baud, out_dir, stop_event)
        workers.append(worker)
        closers.append(worker)
    if not args.no_uno_serial:
        worker = SerialCapture("uno_serial", args.uno_port, args.uno_baud, out_dir, stop_event)
        workers.append(worker)
        closers.append(worker)
    if not args.no_tcp:
        worker = TCPBridgeCapture(args.host, args.tcp_port, out_dir, stop_event)
        workers.append(worker)
        closers.append(worker)
    if not args.no_http_status:
        worker = StatusPollCapture(args.host, args.http_port, args.status_interval, out_dir, stop_event)
        workers.append(worker)
        closers.append(worker)
    if not args.no_http_stream:
        worker = StreamCapture(
            args.host,
            args.stream_port,
            args.save_mjpeg,
            args.stream_stats_interval,
            out_dir,
            stop_event,
        )
        workers.append(worker)
        closers.append(worker)

    for worker in workers:
        worker.start()

    print(f"Capturing to {out_dir}")
    print("Press Ctrl-C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        summary.line("keyboard interrupt received")
        stop_event.set()
    finally:
        for worker in workers:
            worker.join(timeout=3)
        for closer in closers:
            closer.close()
        summary.line("capture stopped")
        summary.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
