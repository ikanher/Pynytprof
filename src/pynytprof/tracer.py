"""Minimal line profiler that writes NYTProf files."""

from __future__ import annotations

import os
import runpy
import struct
import sys
import time
from pathlib import Path
from fnmatch import fnmatch
from types import FrameType
from typing import Any, Dict, List

try:  # optional C acceleration
    from . import _cwrite
except Exception:  # pragma: no cover - absence is fine
    _cwrite = None
try:  # optional C tracer
    from . import _tracer as _ctrace
except Exception:  # pragma: no cover - absence is fine
    _ctrace = None

__all__ = ["profile", "cli", "profile_script"]
__version__ = "0.0.0"

_MAGIC = b"NYTPROF\x00"
TICKS_PER_SEC = 10_000_000  # 100 ns per tick

_results: Dict[int, List[int]] = {}
_start_ns: int = 0
_script_path: Path
_last_ns: int = 0
_filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]


def _match(path: str) -> bool:
    if not _filters:
        return True
    return any(fnmatch(path, pat) for pat in _filters)


def _emit_stub_file(out_path: Path) -> None:
    with out_path.open("wb") as f:
        f.write(_MAGIC)
        f.write(struct.pack("<II", 5, 0))
        f.write(b"E" + struct.pack("<I", 0))


def _chunk(tok: str, payload: bytes) -> bytes:
    return tok.encode() + struct.pack("<I", len(payload)) + payload


def _write_nytprof_py(out_path: Path) -> None:
    if not _results:
        _emit_stub_file(out_path)
        return

    stat = _script_path.stat()
    a_payload = f"ticks_per_sec={TICKS_PER_SEC}\0start_time={_start_ns}\0".encode()
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
        f.write(_MAGIC)
        f.write(struct.pack("<II", 5, 0))
        f.write(_chunk("H", struct.pack("<II", 5, 0)))
        f.write(_chunk("A", a_payload))
        f.write(_chunk("F", f_payload))
        f.write(_chunk("S", b"".join(s_records)))
        f.write(_chunk("E", b""))


def _write_nytprof_vec(out_path: Path, files, defs, calls, lines) -> None:
    if _cwrite is not None:
        _cwrite.write(str(out_path), files, defs, calls, lines, _start_ns, TICKS_PER_SEC)
    else:
        _write_nytprof_py(out_path)


def _trace(frame: FrameType, event: str, arg: Any) -> Any:
    global _last_ns
    path = str(Path(frame.f_code.co_filename).resolve())
    if path != str(_script_path):
        return _trace
    if not _match(path):
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
    global _script_path, _start_ns, _results, _last_ns, _filters
    _filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
    _script_path = Path(path).resolve()
    _start_ns = time.time_ns()
    if _ctrace is not None:
        _ctrace.enable(str(_script_path), _start_ns)
        try:
            runpy.run_path(str(_script_path), run_name="__main__")
        finally:
            defs, calls, lines = _ctrace.dump()
            paths = set()
            for d in defs:
                paths.add(d[1])
            for c in calls:
                if c[0] is not None:
                    paths.add(c[0])
            for s in lines:
                paths.add(s[0])
            files = []
            fid_map = {}
            for i, p in enumerate(sorted(paths)):
                fid_map[p] = i
                st = Path(p).stat()
                files.append((i, 0x10, st.st_size, int(st.st_mtime), p))
            d_records = [(rec[0], fid_map[rec[1]], rec[2], rec[3], rec[4]) for rec in defs]
            c_records = [
                (fid_map.get(rec[0], 0), rec[1], rec[2], rec[3], rec[4])
                for rec in calls
            ]
            s_records = [
                (fid_map[rec[0]], rec[1], rec[2], rec[3], rec[4])
                for rec in lines
            ]
            out_path = Path("nytprof.out")
            _write_nytprof_vec(out_path, files, d_records, c_records, s_records)
        return
    _results = {}
    _last_ns = 0
    out_path = Path("nytprof.out")
    sys.settrace(_trace)
    try:
        runpy.run_path(str(_script_path), run_name="__main__")
    finally:
        sys.settrace(None)
        _write_nytprof_py(out_path)


def profile(path: str) -> None:
    profile_script(path)


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        raise SystemExit(1)
    profile_script(sys.argv[1])


if __name__ == "__main__":
    cli()
