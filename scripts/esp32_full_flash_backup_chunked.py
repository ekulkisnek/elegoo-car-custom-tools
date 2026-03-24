#!/usr/bin/env python3
"""
Full SPI flash backup for ESP32-S3 via esptool, in 1 MiB chunks with retries.
Avoids single long read that can fail mid-stream on noisy USB.

Restore (example — adjust port and path):
  python3 -m esptool --chip esp32s3 -p /dev/cu.usbmodemXXXX -b 115200 \\
    write_flash 0 esp32s3_spi_flash_full.bin
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time

CHUNK_SIZE = 0x100000  # 1 MiB
MAX_RETRIES = 6
DEFAULT_BAUD = 115200


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_esptool_python() -> str:
    venv_py = os.path.join(repo_root(), ".venv-esptool", "bin", "python3")
    if os.path.isfile(venv_py):
        return venv_py
    venv_py2 = os.path.join(repo_root(), ".venv", "bin", "python3")
    if os.path.isfile(venv_py2):
        return venv_py2
    return sys.executable


def run_esptool(py: str, port: str, baud: int, args: list[str]) -> int:
    cmd = [py, "-m", "esptool", "--chip", "esp32s3", "-p", port, "-b", str(baud)] + args
    return subprocess.call(cmd)


def get_flash_size_mb(py: str, port: str, baud: int) -> int:
    """Return flash size in bytes (e.g. 8*1024*1024) using flash_id."""
    p = subprocess.run(
        [py, "-m", "esptool", "--chip", "esp32s3", "-p", port, "-b", str(baud), "flash-id"],
        capture_output=True,
        text=True,
    )
    out = (p.stdout or "") + (p.stderr or "")
    if "8MB" in out or "8 MB" in out:
        return 8 * 1024 * 1024
    if "4MB" in out or "4 MB" in out:
        return 4 * 1024 * 1024
    if "16MB" in out or "16 MB" in out:
        return 16 * 1024 * 1024
    print(out, file=sys.stderr)
    raise SystemExit("Could not parse flash size from flash_id; connect ESP32 and retry.")


def main() -> None:
    default_out = os.path.join(repo_root(), "output", "esp32s3_spi_flash_full.bin")
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--port",
        default=None,
        help="Serial port (default: first /dev/cu.usbmodem*)",
    )
    ap.add_argument("--out", default=default_out, help=f"Output image (default: {default_out})")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    args = ap.parse_args()

    py = find_esptool_python()
    port = args.port
    if not port:
        import glob

        cands = sorted(glob.glob("/dev/cu.usbmodem*"))
        if not cands:
            print("No /dev/cu.usbmodem* — plug in ESP32 USB", file=sys.stderr)
            sys.exit(1)
        port = cands[0]
    print(f"Using Python: {py}")
    print(f"Using port: {port} baud={args.baud}")

    total = get_flash_size_mb(py, port, args.baud)
    print(f"Detected flash size: {total} bytes ({total // (1024*1024)} MiB)")

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, mode=0o755, exist_ok=True)
    tmp_pattern = os.path.join(out_dir, ".chunk_tmp.bin")

    # Fresh output
    if os.path.isfile(args.out):
        os.rename(args.out, args.out + ".previous")

    written = 0
    for offset in range(0, total, CHUNK_SIZE):
        length = min(CHUNK_SIZE, total - offset)
        ok = False
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"Chunk 0x{offset:08x} +{length} bytes (attempt {attempt}/{MAX_RETRIES})...")
            if os.path.isfile(tmp_pattern):
                os.remove(tmp_pattern)
            rc = run_esptool(
                py,
                port,
                args.baud,
                [
                    "read-flash",
                    hex(offset),
                    hex(length),
                    tmp_pattern,
                ],
            )
            if rc == 0 and os.path.isfile(tmp_pattern):
                got = os.path.getsize(tmp_pattern)
                if got == length:
                    ok = True
                    break
                print(f"  Wrong size: got {got} expected {length}", file=sys.stderr)
            else:
                print(f"  esptool exit {rc}", file=sys.stderr)
            time.sleep(1.5)
        if not ok:
            print(f"FAILED at offset 0x{offset:x}", file=sys.stderr)
            sys.exit(2)
        with open(tmp_pattern, "rb") as rf:
            data = rf.read()
        with open(args.out, "ab") as wf:
            wf.write(data)
        os.remove(tmp_pattern)
        written += len(data)
        print(f"  OK — total written {written}/{total}")

    h = hashlib.sha256()
    with open(args.out, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    digest = h.hexdigest()
    print(f"\nDone: {args.out}")
    print(f"Size: {written} bytes")
    print(f"SHA256: {digest}")

    manifest = os.path.join(out_dir, "ESP32_FLASH_BACKUP_MANIFEST.txt")
    with open(manifest, "w") as mf:
        mf.write(f"path={args.out}\n")
        mf.write(f"bytes={written}\n")
        mf.write(f"sha256={digest}\n")
        mf.write(f"port={port}\n")
        mf.write(f"chunk_size=0x{CHUNK_SIZE:x}\n")
        mf.write(
            "\nRestore (full SPI image; put ESP in download mode first):\n"
            f"  python3 -m esptool --chip esp32s3 -p {port} -b 115200 write-flash 0 \\\n"
            f"    {os.path.basename(args.out)}\n"
        )
    print(f"Wrote {manifest}")


if __name__ == "__main__":
    main()
