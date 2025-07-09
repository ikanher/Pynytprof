"""Minimal line profiler that writes NYTProf files."""

from __future__ import annotations

import importlib
import os
import runpy
import warnings
import sys
import time
import argparse
import collections
from pathlib import Path
from fnmatch import fnmatch
from types import FrameType
from typing import Any, Dict, List
import struct

warnings.filterwarnings(
    "ignore",
    message="'pynytprof.tracer' found in sys.modules",
    category=RuntimeWarning,
    module="runpy",
)

_force_py = bool(os.environ.get("PYNTP_FORCE_PY"))
_writer_env = os.environ.get("PYNYTPROF_WRITER")

_write = None
Writer = None
if _writer_env:
    mod = {"py": "_pywrite", "c": "_cwrite"}.get(_writer_env)
    if mod:
        try:
            _mod = importlib.import_module(f"pynytprof.{mod}")
            _write = getattr(_mod, "write", None)
            Writer = getattr(_mod, "Writer", None)
        except ModuleNotFoundError:
            _write = None
            Writer = None
    else:
        raise ImportError(f"unknown writer: {_writer_env}")
elif _force_py:
    try:
        _mod = importlib.import_module("pynytprof._pywrite")
        _write = getattr(_mod, "write", None)
        Writer = getattr(_mod, "Writer", None)
    except ModuleNotFoundError:
        _write = None
        Writer = None
else:
    for _mod_name in ("_writer", "_cwrite", "_pywrite"):
        try:
            _mod = importlib.import_module(f"pynytprof.{_mod_name}")
            _write = getattr(_mod, "write", None)
            Writer = getattr(_mod, "Writer", None)
            break
        except ModuleNotFoundError:  # pragma: no cover - optional
            continue
if Writer is None:
    from ._pywrite import Writer  # type: ignore
if _write is None:  # pragma: no cover - should ship with at least _pywrite
    _write = importlib.import_module("pynytprof._pywrite").write

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
_line_time_ns: collections.Counter[int]
_exc_time_ns: collections.Counter[int]
_calls: collections.Counter[tuple[str, str]]
_call_time_ns: collections.Counter[str]
_edge_time_ns: collections.Counter[tuple[str, str]]
_last_ts: int = 0
_stack: list[tuple[int | None, int]]
_call_stack: list[tuple[str, int]]
_start_ns: int = 0
_script_path: Path
_filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]


def _match(path: str) -> bool:
    if not _filters:
        return True
    return any(fnmatch(path, pat) for pat in _filters)


def _emit_f(writer: Writer) -> None:
    import os, struct

    st = os.stat(_script_path)
    payload = (
        struct.pack(
            "<IIII",
            0,
            0x10,
            st.st_size,
            int(st.st_mtime),
        )
        + str(_script_path).encode()
        + b"\0"
    )
    writer.write_chunk(b"F", payload)


def _write_nytprof(out_path: Path) -> None:
    with Writer(str(out_path), start_ns=_start_ns, ticks_per_sec=TICKS_PER_SEC) as w:
        _emit_f(w)

        if _write.__module__.endswith("_pywrite") and _calls:
            id_map = {}
            for name in sorted({n for pair in _calls for n in pair}):
                sid = len(id_map)
                id_map[name] = sid
            d_parts = [
                struct.pack("<II", sid, 0) + name.encode() + b"\0"
                for name, sid in id_map.items()
            ]
            if d_parts:
                w.write_chunk(b"D", b"".join(d_parts))

            c_parts = []
            ns2ticks = lambda ns: ns // 100
            for (caller, callee), cnt in _calls.items():
                inc = ns2ticks(_edge_time_ns.get((caller, callee), 0))
                c_parts.append(
                    struct.pack("<IIIQQ", id_map[caller], id_map[callee], cnt, inc, inc)
                )
            if c_parts:
                w.write_chunk(b"C", b"".join(c_parts))

        s_parts = [
            struct.pack(
                "<IIIQQ",
                0,
                line,
                calls,
                _line_time_ns[line] // 100,
                _exc_time_ns.get(line, 0) // 100,
            )
            for line, calls in sorted(_line_hits.items())
        ]
        if s_parts:
            w.write_chunk(b"S", b"".join(s_parts))


def _write_nytprof_vec(out_path: Path, files, defs, calls, lines) -> None:
    with Writer(str(out_path), start_ns=_start_ns, ticks_per_sec=TICKS_PER_SEC) as w:
        _emit_f(w)

        if defs:
            d_payload = b"".join(
                struct.pack("<IIII", sid, fid, sl, el) + name.encode() + b"\0"
                for sid, fid, sl, el, name in defs
            )
            w.write_chunk(b"D", d_payload)

        if calls:
            c_payload = b"".join(
                struct.pack("<IIIQQ", fid, line, sid, inc // 100, exc // 100)
                for fid, line, sid, inc, exc in calls
            )
            w.write_chunk(b"C", c_payload)

        if lines:
            s_payload = b"".join(
                struct.pack("<IIIQQ", fid, line, cnt, inc // 100, exc // 100)
                for fid, line, cnt, inc, exc in lines
            )
            w.write_chunk(b"S", s_payload)


def _trace(frame: FrameType, event: str, arg: Any) -> Any:
    global _last_ts
    path = str(Path(frame.f_code.co_filename).resolve())
    if path != str(_script_path):
        return _trace
    if not _match(path):
        return _trace
    now = time.perf_counter_ns()
    if event == "call":
        callee = frame.f_code.co_name
        caller = (
            frame.f_back.f_code.co_name if frame.f_back else "<toplevel>"
        )
        _calls[(caller, callee)] += 1
        _stack.append((None, now))
        _call_stack.append((callee, now))
    elif event == "return":
        if _stack:
            lineno, start = _stack.pop()
            delta = now - start
            if lineno is not None:
                _exc_time_ns[lineno] += delta
        if _call_stack:
            func, start = _call_stack.pop()
            dur = now - start
            _call_time_ns[func] += dur
            if _call_stack:
                caller = _call_stack[-1][0]
                _edge_time_ns[(caller, func)] += dur
    elif event == "line":
        delta = now - _last_ts
        lineno = frame.f_lineno
        _line_hits[lineno] += 1
        _line_time_ns[lineno] += delta
        _last_ts = now
        if _stack:
            pline, pstart = _stack[-1]
            if pline is not None:
                _exc_time_ns[pline] += now - pstart
            _stack[-1] = (frame.f_lineno, now)
        else:
            _stack.append((frame.f_lineno, now))
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
    global _line_hits, _line_time_ns, _exc_time_ns, _calls, _call_time_ns
    global _edge_time_ns, _last_ts, _stack, _call_stack
    _line_hits = collections.Counter()
    _line_time_ns = collections.Counter()
    _exc_time_ns = collections.Counter()
    _calls = collections.Counter()
    _call_time_ns = collections.Counter()
    _edge_time_ns = collections.Counter()
    _last_ts = time.perf_counter_ns()
    _stack = []
    _call_stack = []
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        runpy.run_path(str(_script_path), run_name="__main__")
    finally:
        sys.settrace(None)
        _write_nytprof(out_p)


def profile_command(code: str, out_path: Path | str = "nytprof.out") -> None:
    global _script_path, _start_ns, _results, _filters, _line_hits, _line_time_ns
    global _exc_time_ns, _calls, _call_time_ns, _edge_time_ns, _last_ts, _stack
    global _call_stack
    _filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
    _script_path = Path(sys.argv[0]).resolve()
    _start_ns = time.time_ns()
    _results = {}
    _line_hits = collections.Counter()
    _line_time_ns = collections.Counter()
    _exc_time_ns = collections.Counter()
    _calls = collections.Counter()
    _call_time_ns = collections.Counter()
    _edge_time_ns = collections.Counter()
    _last_ts = time.perf_counter_ns()
    _stack = []
    _call_stack = []
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        exec(code, {"__name__": "__main__"})
    finally:
        sys.settrace(None)
        lines_vec = [
            (
                0,
                line,
                calls,
                _line_time_ns[line],
                _exc_time_ns.get(line, 0),
            )
            for line, calls in sorted(_line_hits.items())
        ]
        with Writer(str(out_p), start_ns=_start_ns, ticks_per_sec=TICKS_PER_SEC) as w:
            _emit_f(w)
            if lines_vec:
                payload = b"".join(
                    struct.pack(
                        "<IIIQQ",
                        fid,
                        line,
                        calls_v,
                        inc // 100,
                        exc // 100,
                    )
                    for fid, line, calls_v, inc, exc in lines_vec
                )
                w.write_chunk(b"S", payload)


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
