"""Line-level profiler emitting NYTProf HAFSE chunks."""

from __future__ import annotations

__all__ = ["profile_script", "cli"]

import io
import runpy
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

TICKS_PER_SEC = 10_000_000
MAGIC = b"NYTPROF\0"

# aggregation dict: {line: {"calls": int, "inc_ns": int, "exc_ns": int}}
LINE_DATA: dict[int, dict[str, int]] = {}


@dataclass
class _Frame:
    start: int
    last: int
    line: int | None
    caller_line: int | None


def _trace_factory(stack: list[_Frame], path: str):
    start_wall = None
    start_perf = None

    def record(line: int, inc: int, exc: int, calls: int = 0) -> None:
        rec = LINE_DATA.setdefault(line, {"calls": 0, "inc_ns": 0, "exc_ns": 0})
        rec["inc_ns"] += inc
        rec["exc_ns"] += exc
        if calls:
            rec["calls"] += calls

    def tracer(frame, event, arg):
        nonlocal start_wall, start_perf
        if sys.gettrace() is not tracer:
            return None
        now = time.perf_counter_ns()
        if start_perf is None:
            start_perf = now
            start_wall = time.time_ns()
        if event == "call":
            if stack:
                parent = stack[-1]
                if parent.line is not None:
                    dt = now - parent.last
                    record(parent.line, dt, dt)
                parent.last = now
            caller_line = stack[-1].line if stack else None
            stack.append(_Frame(now, now, None, caller_line))
            return tracer
        if not stack:
            return tracer
        cur = stack[-1]
        if event == "line":
            if cur.line is not None:
                dt = now - cur.last
                record(cur.line, dt, dt)
            cur.line = frame.f_lineno
            cur.last = now
            record(cur.line, 0, 0, 1)
        elif event == "return":
            if cur.line is not None:
                dt = now - cur.last
                record(cur.line, dt, dt)
            total = now - cur.start
            stack.pop()
            if stack and cur.caller_line is not None:
                record(cur.caller_line, total, 0)
                stack[-1].last = now
        elif event == "exception":
            if cur.line is not None:
                dt = now - cur.last
                record(cur.line, dt, dt)
            cur.last = now
        elif event == "c_call":
            if stack:
                parent = stack[-1]
                if parent.line is not None:
                    dt = now - parent.last
                    record(parent.line, dt, dt)
                parent.last = now
            caller_line = stack[-1].line if stack else None
            stack.append(_Frame(now, now, None, caller_line))
        elif event in {"c_return", "c_exception"}:
            stack.pop()
            if stack:
                parent = stack[-1]
                if parent.line is not None:
                    record(parent.line, now - parent.last, 0)
                parent.last = now
        return tracer

    tracer.start_wall = lambda: start_wall
    return tracer


def _write_file(out: Path, script: str, start: int) -> None:
    abs_path = str(Path(script).resolve())
    st = Path(script).stat()
    buf = io.BytesIO()
    buf.write(MAGIC)
    buf.write(struct.pack("<II", 5, 0))

    def chunk(tok: bytes, payload: bytes) -> None:
        buf.write(tok)
        buf.write(struct.pack("<I", len(payload)))
        buf.write(payload)

    chunk(b"H", struct.pack("<II", 5, 0))
    a = f"ticks_per_sec={TICKS_PER_SEC}\0start_time={start}\0".encode()
    chunk(b"A", a)
    f_payload = struct.pack("<IIII", 0, 0x10, st.st_size, int(st.st_mtime))
    f_payload += abs_path.encode() + b"\0"
    chunk(b"F", f_payload)
    s_buf = io.BytesIO()
    for line in sorted(LINE_DATA):
        rec = LINE_DATA[line]
        s_buf.write(
            struct.pack(
                "<IIIQQ",
                0,
                line,
                rec["calls"],
                rec["inc_ns"] // 100,
                rec["exc_ns"] // 100,
            )
        )
    chunk(b"S", s_buf.getvalue())
    chunk(b"E", b"")
    out.write_bytes(buf.getvalue())


def profile_script(path: str) -> None:
    LINE_DATA.clear()
    stack: list[_Frame] = []
    tracer = _trace_factory(stack, path)
    sys.settrace(tracer)
    try:
        runpy.run_path(path, run_name="__main__")
    finally:
        sys.settrace(None)
        start_wall = tracer.start_wall()
        if start_wall is None:
            start_wall = time.time_ns()
        _write_file(Path("nytprof.out"), path, start_wall)


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        sys.exit(1)
    profile_script(sys.argv[1])


if __name__ == "__main__":
    cli()
