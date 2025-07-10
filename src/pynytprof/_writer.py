from __future__ import annotations

import os
import warnings
import struct
import time
from pathlib import Path

import importlib.metadata

from ._pywrite import _make_ascii_header, write as _py_write

_version = importlib.metadata.version("pynytprof")


class Writer:
    """Pure Python NYTProf writer used when the C extension is unavailable."""

    def __init__(
        self,
        path: str,
        start_ns: int | None = None,
        ticks_per_sec: int = 10_000_000,
        tracer=None,
    ) -> None:
        self._path = Path(path)
        self._fh = None
        self.start_time = time.time_ns() if start_ns is None else start_ns
        self.ticks_per_sec = ticks_per_sec
        self._start_ns = self.start_time
        self.tracer = tracer
        self.writer = self
        self._line_hits: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._buf: dict[bytes, bytearray] = {
            b"F": bytearray(),
            b"S": bytearray(),
            b"D": bytearray(),
            b"C": bytearray(),
        }

    def _buffer_chunk(self, tag: bytes, payload: bytes) -> None:
        if payload:
            self._buf[tag].extend(payload)

    def record_line(self, fid: int, line: int, calls: int, inc: int, exc: int) -> None:
        self._line_hits[(fid, line)] = (calls, inc, exc)
        rec = struct.pack("<IIIQQ", fid, line, calls, inc, exc)
        self._buffer_chunk(b"S", rec)

    # expose the same API the C writer has
    def write_chunk(self, token: bytes, payload: bytes) -> None:  # noqa: D401 - simple delegate
        tag = token[:1]
        if tag in self._buf:
            self._buffer_chunk(tag, payload)
        elif tag == b"E":
            pass  # handled on close

    def __enter__(self) -> "Writer":
        self._fh = open(self._path, "wb")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if not self._fh:
            return

        if self.tracer is not None:
            ns2ticks = lambda ns: ns // 100
            for line, calls in self.tracer._line_hits.items():
                rec = struct.pack(
                    "<IIIQQ",
                    0,
                    line,
                    calls,
                    ns2ticks(self.tracer._line_time_ns[line]),
                    ns2ticks(self.tracer._exc_time_ns.get(line, 0)),
                )
                self._buffer_chunk(b"S", rec)

        if not self._buf[b"S"]:
            recs = []
            for (fid, line), (calls, inc, exc) in self._line_hits.items():
                recs.append(struct.pack("<IIIQQ", fid, line, calls, inc, exc))
            if recs:
                self._buffer_chunk(b"S", b"".join(recs))

        hdr = _make_ascii_header(self._start_ns)
        self._fh.write(hdr)
        for tag in [b"F", b"S", b"D", b"C", b"E"]:
            payload = self._buf.get(tag, b"") if tag != b"E" else b""
            self._fh.write(tag)
            self._fh.write(len(payload).to_bytes(4, "little"))
            self._fh.write(payload)

        self._fh.close()
        self._fh = None


_mode = os.environ.get("PYNYTPROF_WRITER", "auto")

if _mode == "c":
    try:
        from . import _cwrite as _impl
    except Exception:
        _impl = None
    if _impl is not None and getattr(_impl, "__build__", None) == _version:
        write = _impl.write
        Writer = getattr(_impl, "Writer", Writer)
    else:
        if _impl is not None and getattr(_impl, "__build__", None) != _version:
            warnings.warn(
                "stale _cwrite extension; falling back to pure-Python writer",
                RuntimeWarning,
            )
        write = _py_write
else:  # "py" or auto fallback
    write = _py_write

__all__ = ["write", "Writer"]
