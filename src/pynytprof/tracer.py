"""Minimal line profiler that writes NYTProf files."""

from __future__ import annotations

import importlib
import os
import runpy
import sys
import time
import argparse
import collections
from pathlib import Path
from fnmatch import fnmatch
from types import FrameType
from typing import Any, Dict, List

_force_py = bool(os.environ.get("PYNTP_FORCE_PY"))
_writer_env = os.environ.get("PYNYTPROF_WRITER")

_write = None
if _writer_env:
    mod = {"py": "_pywrite", "c": "_cwrite"}.get(_writer_env)
    if mod:
        try:
            _write = importlib.import_module(f"pynytprof.{mod}").write
        except ModuleNotFoundError:
            _write = None
    else:
        raise ImportError(f"unknown writer: {_writer_env}")
elif _force_py:
    try:
        _write = importlib.import_module("pynytprof._pywrite").write
    except ModuleNotFoundError:
        _write = None
else:
    for _mod in ("_writer", "_cwrite", "_pywrite"):
        try:
            _write = importlib.import_module(f"pynytprof.{_mod}").write
            break
        except ModuleNotFoundError:  # pragma: no cover - optional
            continue
if _write is None:  # pragma: no cover - should ship with at least _pywrite
    raise ImportError("No nyprof writer available")

_ctrace = None
if not _force_py:
    for _mod in ("_ctrace", "_tracer", "_tracer_py"):
        try:
            _ctrace = importlib.import_module(f"pynytprof.{_mod}")
            break
        except ModuleNotFoundError:  # pragma: no cover - optional
            continue

__all__ = ["profile", "cli", "profile_script", "main", "profile_command"]
try:
    from ._version import version as __version__
except Exception:
    __version__ = "0.0.0"
TICKS_PER_SEC = 10_000_000  # 100 ns per tick

_results: Dict[int, List[int]] = {}
_line_hits: collections.Counter[int]
_start_ns: int = 0
_script_path: Path
_filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]


def _match(path: str) -> bool:
    if not _filters:
        return True
    return any(fnmatch(path, pat) for pat in _filters)


def _write_nytprof(out_path: Path) -> None:
    stat = _script_path.stat()
    files = [(0, 0x10, stat.st_size, int(stat.st_mtime), str(_script_path))]
    lines_vec = [(0, line, calls, 0, 0) for line, calls in sorted(_line_hits.items())]
    _write(str(out_path), files, [], [], lines_vec, _start_ns, TICKS_PER_SEC)

    import subprocess
    import shutil

    if shutil.which("xxd"):
        subprocess.run(["xxd", "-g1", "-l64", out_path], text=True)


def _write_nytprof_vec(out_path: Path, files, defs, calls, lines) -> None:
    _write(
        str(out_path),
        files,
        defs,
        calls,
        lines,
        _start_ns,
        TICKS_PER_SEC,
    )


def _trace(frame: FrameType, event: str, arg: Any) -> Any:
    path = str(Path(frame.f_code.co_filename).resolve())
    if path != str(_script_path):
        return _trace
    if not _match(path):
        return _trace
    if event == "line":
        _line_hits[frame.f_lineno] += 1
    return _trace


def profile_script(path: str, out_path: Path | str = "nytprof.out") -> None:
    global _script_path, _start_ns, _results, _filters, _line_hits
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
            c_records = [(fid_map.get(rec[0], 0), rec[1], rec[2], rec[3], rec[4]) for rec in calls]
            s_records = [(fid_map[rec[0]], rec[1], rec[2], rec[3], rec[4]) for rec in lines]
            _write_nytprof_vec(Path(out_path), files, d_records, c_records, s_records)
        return
    _results = {}
    global _line_hits
    _line_hits = collections.Counter()
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        runpy.run_path(str(_script_path), run_name="__main__")
    finally:
        sys.settrace(None)
        _write_nytprof(out_p)


def profile_command(code: str, out_path: Path | str = "nytprof.out") -> None:
    global _script_path, _start_ns, _results, _filters, _line_hits
    _filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
    _script_path = Path("-e")
    _start_ns = time.time_ns()
    _results = {}
    _line_hits = collections.Counter()
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        exec(code, {"__name__": "__main__"})
    finally:
        sys.settrace(None)
        lines_vec = [(0, line, calls, 0, 0) for line, calls in sorted(_line_hits.items())]
        _write(str(out_p), [], [], [], lines_vec, _start_ns, TICKS_PER_SEC)


def profile(path: str) -> None:
    profile_script(path)


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        raise SystemExit(1)
    profile_script(sys.argv[1])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pynytprof.tracer")
    parser.add_argument("-o", "--output", type=Path, default="nytprof.out")
    parser.add_argument("-e", dest="expr", default=None)
    parser.add_argument("script", nargs="?")
    parser.add_argument("args", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)
    if ns.expr is not None:
        if ns.script:
            parser.error("cannot use -e with script")
        profile_command(ns.expr, ns.output)
    else:
        if not ns.script:
            parser.error("missing script")
        sys.argv = [ns.script] + ns.args
        profile_script(ns.script, ns.output)


if __name__ == "__main__":
    main()
