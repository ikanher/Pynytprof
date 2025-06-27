"""Minimal line profiler that writes NYTProf files."""

from __future__ import annotations

import runpy
import struct
import sys
import time
from pathlib import Path
from types import FrameType
from typing import Any, Dict, List

__all__ = ["profile", "cli", "profile_script"]
__version__ = "0.0.0"

MAGIC = b"NYTPROF"
TICKS_PER_SEC = 10_000_000  # 100 ns per tick

_results: Dict[int, List[int]] = {}
_start_ns: int = 0
_script_path: Path
_last_ns: int = 0


def _emit_stub_file(out_path: Path) -> None:
    with out_path.open("wb") as f:
        f.write(MAGIC + b"\0")
        f.write(struct.pack("<II", 5, 0))
        f.write(b"E" + struct.pack("<I", 0))


def _chunk(tok: str, payload: bytes) -> bytes:
    return tok.encode() + struct.pack("<I", len(payload)) + payload


def _write_nytprof(out_path: Path) -> None:
    if not _results:
        _emit_stub_file(out_path)
        return

    stat = _script_path.stat()
    a_payload = (
        f"ticks_per_sec={TICKS_PER_SEC}\0start_time={_start_ns}\0".encode()
    )
    f_payload = (
        struct.pack("<IIII", 0, 0x10, stat.st_size, int(stat.st_mtime))
        + str(_script_path).encode()
        + b"\0"
    )
    s_records = [
        struct.pack("<IIIQQ", 0, line, rec[0], rec[1] // 100, rec[2] // 100)
        for line, rec in sorted(_results.items())
    ]
    if not s_records:
        _emit_stub_file(out_path)
        return

    with out_path.open("wb") as f:
        f.write(MAGIC + b"\0")
        f.write(struct.pack("<II", 5, 0))
        f.write(_chunk("H", struct.pack("<II", 5, 0)))
        f.write(_chunk("A", a_payload))
        f.write(_chunk("F", f_payload))
        f.write(_chunk("S", b"".join(s_records)))
        f.write(_chunk("E", b""))


def _trace(frame: FrameType, event: str, arg: Any) -> Any:
    global _last_ns
    if frame.f_code.co_filename != str(_script_path):
        return _trace
    if event == "line":
        now = time.perf_counter_ns()
        dt = 0 if _last_ns == 0 else now - _last_ns
        rec = _results.setdefault(frame.f_lineno, [0, 0, 0])
        rec[0] += 1
        rec[1] += dt
        rec[2] += dt
        _last_ns = now
    return _trace


def profile_script(path: str) -> None:
    global _script_path, _start_ns, _results, _last_ns
    _script_path = Path(path).resolve()
    _start_ns = time.time_ns()
    _results = {}
    _last_ns = 0
    out_path = Path("nytprof.out")
    sys.settrace(_trace)
    try:
        runpy.run_path(str(_script_path), run_name="__main__")
    finally:
        sys.settrace(None)
        _write_nytprof(out_path)


def profile(path: str) -> None:
    profile_script(path)


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        raise SystemExit(1)
    profile_script(sys.argv[1])

if __name__ == "__main__":
    cli()

