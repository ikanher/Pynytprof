"""Pure-Python tracer that writes a minimal NYTProf stream."""

from __future__ import annotations

__all__ = ["profile_script", "cli"]

import os
import runpy
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass
class _FrameInfo:
    start_ns: int
    last_ns: int
    prev_line: int
    call_line: int | None
    filename: str


# results[(fid, line)] = {"calls": int, "inc": ns, "exc": ns}
_results: Dict[Tuple[int, int], Dict[str, int]] = {}
_stack: Dict[object, _FrameInfo] = {}
_start_unix_ns: int | None = None
_script_path: str


def _add_exc(line: int, delta: int) -> None:
    ent = _results.setdefault((0, line), {"calls": 0, "inc": 0, "exc": 0})
    ent["exc"] += delta
    ent["inc"] += delta


def _inc_line(line: int) -> None:
    _results.setdefault((0, line), {"calls": 0, "inc": 0, "exc": 0})["calls"] += 1


def _trace(frame, event, arg):
    global _start_unix_ns
    now = time.perf_counter_ns()
    if _start_unix_ns is None:
        _start_unix_ns = time.time_ns()
    if event == "call":
        parent = _stack.get(frame.f_back)
        if parent:
            d = now - parent.last_ns
            if parent.filename == _script_path:
                _add_exc(parent.prev_line, d)
            parent.last_ns = now
        call_line = None
        if frame.f_back and frame.f_back.f_code.co_filename == _script_path:
            call_line = frame.f_back.f_lineno
        rec = _FrameInfo(now, now, frame.f_lineno, call_line, frame.f_code.co_filename)
        _stack[frame] = rec
        return _trace
    rec = _stack.get(frame)
    if not rec:
        return _trace
    if event == "line":
        d = now - rec.last_ns
        if rec.filename == _script_path:
            _add_exc(rec.prev_line, d)
            _inc_line(frame.f_lineno)
            rec.prev_line = frame.f_lineno
        rec.last_ns = now
        return _trace
    if event == "return":
        d = now - rec.last_ns
        if rec.filename == _script_path:
            _add_exc(rec.prev_line, d)
        duration = now - rec.start_ns
        if rec.call_line is not None:
            _results.setdefault((0, rec.call_line), {"calls": 0, "inc": 0, "exc": 0})[
                "inc"
            ] += duration
        _stack.pop(frame, None)
        parent = _stack.get(frame.f_back)
        if parent:
            parent.last_ns = now
        return _trace
    return _trace


def _write_nytprof(out_path: Path) -> None:
    st = os.stat(_script_path)
    with out_path.open("wb") as f:
        f.write(b"NYTPROF\0")
        f.write(struct.pack("<II", 5, 0))

        def chunk(tok: str, payload: bytes) -> None:
            f.write(tok.encode("ascii"))
            f.write(struct.pack("<I", len(payload)))
            f.write(payload)

        chunk("H", struct.pack("<II", 5, 0))
        props = f"ticks_per_sec=10000000\x00start_time={_start_unix_ns}\x00".encode()
        chunk("A", props)
        path_bytes = _script_path.encode() + b"\x00"
        chunk("F", struct.pack("<IIII", 0, 0x10, st.st_size, int(st.st_mtime)) + path_bytes)
        records = []
        for (fid, line), ent in sorted(_results.items()):
            records.append(
                struct.pack(
                    "<IIIQQ",
                    fid,
                    line,
                    ent["calls"],
                    ent["inc"] // 100,
                    ent["exc"] // 100,
                )
            )
        chunk("S", b"".join(records))
        chunk("E", b"")


def profile_script(path: str) -> None:
    global _script_path, _results, _stack, _start_unix_ns
    _results = {}
    _stack = {}
    _start_unix_ns = None
    _script_path = os.path.abspath(path)
    sys.settrace(_trace)
    try:
        runpy.run_path(_script_path, run_name="__main__")
    finally:
        sys.settrace(None)
    _write_nytprof(Path("nytprof.out"))


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        sys.exit(1)
    profile_script(sys.argv[1])


if __name__ == "__main__":  # allow `python -m pynytprof.tracer` directly
    cli()
