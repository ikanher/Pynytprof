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

from ._writer import WRITER as Writer

try:
    from ._version import version as __version__
except Exception:
    __version__ = "0.0.0"

warnings.filterwarnings(
    "ignore",
    message="'pynytprof.tracer' found in sys.modules",
    category=RuntimeWarning,
    module="runpy",
)

_force_py = bool(os.environ.get("PYNTP_FORCE_PY"))  # preserved for _ctrace logic

_ctrace = None
if not _force_py:
    for _mod in ("_ctrace", "_tracer", "_tracer_py"):
        try:
            _ctrace = importlib.import_module(f"pynytprof.{_mod}")
            break
        except ModuleNotFoundError:  # pragma: no cover - optional
            continue

__all__ = ["profile", "cli", "profile_script", "main", "profile_command"]
TICKS_PER_SEC = 10_000_000  # 100 ns per tick

_results: Dict[int, List[int]] = {}
_line_hits: Dict[tuple[int, int], list[int]]
_calls: collections.Counter[tuple[str, str]]
_call_time_ns: collections.Counter[str]
_edge_time_ns: collections.Counter[tuple[str, str]]
_last_ts: int = 0
_stack: list[tuple[int | None, int]]
_call_stack: list[tuple[str, int]]
_start_ns: int = 0
_script_path: Path
_filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
_emitted_f: bool = False
_stmt_records: list[tuple[int, int, int]]


def _match(path: str) -> bool:
    if not _filters:
        return True
    return any(fnmatch(path, pat) for pat in _filters)


def _emit_f(writer: Writer) -> None:
    global _emitted_f
    if _emitted_f:
        return
    _emitted_f = True
    import os
    import struct

    st = os.stat(_script_path)
    fields = struct.pack(
        "<IIII",
        0,  # fid
        0x10,  # flags HAS_SRC
        st.st_size,
        int(st.st_mtime),
    )
    path_b = str(_script_path).encode()
    payload = fields + path_b + b"\0"
    writer.write_chunk(b"F", payload)


def _emit_p(writer: Writer) -> None:
    import os
    import time
    import struct

    pid = os.getpid()
    ppid = os.getppid()
    start = time.time()
    payload = struct.pack('<IId', pid, ppid, start)
    writer.write_chunk(b"P", payload)


def _write_nytprof(out_path: Path) -> None:
    try:
        w = Writer(
            str(out_path),
            start_ns=_start_ns,
            ticks_per_sec=TICKS_PER_SEC,
            script_path=str(_script_path),
        )
    except TypeError:
        w = Writer(str(out_path), start_ns=_start_ns, ticks_per_sec=TICKS_PER_SEC)
    if os.environ.get("PYNYTPROF_DEBUG"):
        print(
            f"USING WRITER: {w.__class__.__module__}.{w.__class__.__name__}",
            file=sys.stderr,
        )
    w.__enter__()
    try:
        import struct

        emitted_d = False
        d_payload = b""
        if hasattr(w, "_stmt_records"):
            w._stmt_records.extend(_stmt_records)
            emitted_d = bool(_stmt_records)
        elif _stmt_records:
            buf = bytearray()
            fid = w._register_file(str(_script_path))
            for _, line, dur in _stmt_records:
                buf += struct.pack("<BIIQ", 1, fid, line, dur)
            buf.append(0)
            d_payload = bytes(buf)
            emitted_d = True

        fid = w._register_file(str(_script_path))
        recs = []
        for (_, line), (calls, inc, exc) in sorted(_line_hits.items()):
            recs.append(
                struct.pack(
                    "<IIIQQ",
                    fid,
                    line,
                    calls,
                    inc,
                    exc,
                )
            )
        payload = b"".join(recs)
        if payload:
            w.write_chunk(b"S", payload)
        if d_payload:
            w.write_chunk(b"D", d_payload)

        emitted_c = False
        if _calls:
            id_map = {}
            for name in sorted({n for pair in _calls for n in pair}):
                id_map[name] = len(id_map)

            def ns2ticks(ns: int) -> int:
                return ns // 100

            c_parts = []
            for (caller, callee), cnt in _calls.items():
                inc = ns2ticks(_edge_time_ns.get((caller, callee), 0))
                c_parts.append(
                    struct.pack("<IIIQQ", id_map[caller], id_map[callee], cnt, inc, inc)
                )
            if c_parts:
                w.write_chunk(b"C", b"".join(c_parts))
                emitted_c = True

        if not emitted_d:
            w.write_chunk(b"D", b"")
        if not emitted_c:
            w.write_chunk(b"C", b"")
    finally:
        if getattr(w, "finalize", None):
            w.finalize()
        elif getattr(w, "close", None):
            w.close()


def _write_nytprof_vec(out_path: Path, files, defs, calls, lines) -> None:
    with Writer(str(out_path), start_ns=_start_ns, ticks_per_sec=TICKS_PER_SEC) as w:
        if os.environ.get("PYNYTPROF_DEBUG"):
            print(
                f"USING WRITER: {w.__class__.__module__}.{w.__class__.__name__}",
                file=sys.stderr,
            )
        if lines:
            s_payload = b"".join(
                struct.pack("<IIIQQ", fid, line, cnt, inc // 100, exc // 100)
                for fid, line, cnt, inc, exc in lines
            )
            w.write_chunk(b"S", s_payload)

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
        caller = frame.f_back.f_code.co_name if frame.f_back else "<toplevel>"
        _calls[(caller, callee)] += 1
        _stack.append((None, now))
        _call_stack.append((callee, now))
    elif event == "return":
        if _stack:
            lineno, start = _stack.pop()
            delta = now - start
            if lineno is not None:
                key = (0, lineno)
                rec = _line_hits.get(key)
                if rec is None:
                    rec = [0, 0, 0]
                    _line_hits[key] = rec
                rec[2] += delta // 100
            if _stack:
                c_line, c_start = _stack[-1]
                if c_line is not None:
                    ckey = (0, c_line)
                    crec = _line_hits.get(ckey)
                    if crec is None:
                        crec = [0, 0, 0]
                        _line_hits[ckey] = crec
                    crec[1] += (now - c_start) // 100
                    _stack[-1] = (c_line, now)
        _last_ts = now
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
        key = (0, lineno)
        rec = _line_hits.get(key)
        if rec is None:
            rec = [0, 0, 0]
            _line_hits[key] = rec
        rec[0] += 1
        rec[1] += delta // 100
        _stmt_records.append((0, lineno, delta))
        _last_ts = now
        if _stack:
            pline, pstart = _stack[-1]
            if pline is not None:
                pkey = (0, pline)
                prec = _line_hits.get(pkey)
                if prec is None:
                    prec = [0, 0, 0]
                    _line_hits[pkey] = prec
                prec[2] += (now - pstart) // 100
            _stack[-1] = (frame.f_lineno, now)
        else:
            _stack.append((frame.f_lineno, now))
    return _trace


def profile_script(path: str, out_path: Path | str | None = None) -> None:
    global _script_path, _start_ns, _results, _filters, _line_hits, _emitted_f
    global _stmt_records
    _filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
    _script_path = Path(path).resolve()
    _emitted_f = False
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
    global _line_hits, _calls, _call_time_ns
    global _edge_time_ns, _last_ts, _stack, _call_stack
    _line_hits = {}
    _calls = collections.Counter()
    _call_time_ns = collections.Counter()
    _edge_time_ns = collections.Counter()
    _last_ts = time.perf_counter_ns()
    _stack = []
    _call_stack = []
    _stmt_records = []
    if out_path is None:
        out_path = f"nytprof.out.{os.getpid()}"
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        runpy.run_path(str(_script_path), run_name="__main__")
    finally:
        sys.settrace(None)
        _write_nytprof(out_p)


def profile_command(code: str, out_path: Path | str | None = None) -> None:
    global _script_path, _start_ns, _results, _filters, _line_hits
    global _calls, _call_time_ns, _edge_time_ns, _last_ts, _stack
    global _call_stack, _emitted_f, _stmt_records
    _filters = [p for p in os.environ.get("NYTPROF_FILTER", "").split(",") if p]
    _script_path = Path(sys.argv[0]).resolve()
    _emitted_f = False
    _start_ns = time.time_ns()
    _results = {}
    _line_hits = {}
    _calls = collections.Counter()
    _call_time_ns = collections.Counter()
    _edge_time_ns = collections.Counter()
    _last_ts = time.perf_counter_ns()
    _stack = []
    _call_stack = []
    _stmt_records = []
    if out_path is None:
        out_path = f"nytprof.out.{os.getpid()}"
    out_p = Path(out_path)
    sys.settrace(_trace)
    try:
        compiled = compile(code, str(_script_path), "exec")
        exec(compiled, {"__name__": "__main__"})
    finally:
        sys.settrace(None)
        _write_nytprof(out_p)


def profile(path: str) -> None:
    profile_script(path)


def cli() -> None:
    if len(sys.argv) != 2:
        print("Usage: pynytprof <script.py>", file=sys.stderr)
        raise SystemExit(1)
    profile_script(sys.argv[1])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pynytprof.tracer")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=f"nytprof.out.{os.getpid()}",
    )
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
