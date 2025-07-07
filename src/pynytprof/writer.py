from __future__ import annotations

import os
import struct
import time
from pathlib import Path
import zlib

__all__ = ["Writer"]

PREFIX = b"NYTPROF\0"
VERSION = 5


class Writer:
    """Minimal NYTProf file writer used for tests."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._fh: os.PathLike | None = None
        self._header_written = False
        self._header_bytes = b""
        self._compressed_used = False

    def _compress(self, tag: bytes, data: bytes) -> bytes:
        if data and tag in {b"F", b"D", b"C", b"S"}:
            self._compressed_used = True
            return zlib.compress(data, 6)
        return data

    def _add_compressed_flag(self) -> None:
        data = self._path.read_bytes()
        rest = data[len(self._header_bytes) :]
        lines = self._header_bytes.rstrip(b"\n").split(b"\n")
        if lines and lines[-1] == b"":
            lines = lines[:-1]
        lines.append(b"compressed=1")
        lines.append(b"")
        new_header = b"\n".join(lines) + b"\n"
        self._path.write_bytes(new_header + rest)
        self._header_bytes = new_header

    def __enter__(self) -> "Writer":
        self._fh = self._path.open("wb")
        self._write_text_header()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh:
            self._fh.close()
        self._fh = None
        if self._compressed_used and b"compressed=1\n" not in self._header_bytes:
            self._add_compressed_flag()
        self._header_written = False

    def _write_text_header(self) -> None:
        if self._header_written or self._fh is None:
            return
        lines = [
            f"file={self._path}",
            "version=5",
            "ticks_per_sec=1000000000",
            f"process_id={os.getpid()}",
            f"start_time={int(time.time())}",
        ]
        if self._compressed_used:
            lines.append("compressed=1")
        lines.append("")
        header = b"\n".join(line.encode("ascii") for line in lines) + b"\n"
        self._fh.write(header)
        self._header_bytes = header
        self._header_written = True

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = self._compress(tag, payload)
        self._fh.write(tag)
        self._fh.write(struct.pack("<I", len(payload)))
        if payload:
            self._fh.write(payload)
