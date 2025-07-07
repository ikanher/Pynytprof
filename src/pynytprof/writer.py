from __future__ import annotations

import os
import struct
import time
from pathlib import Path

__all__ = ["Writer"]

PREFIX = b"NYTPROF\0"
VERSION = 5


class Writer:
    """Minimal NYTProf file writer used for tests."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._fh: os.PathLike | None = None
        self._header_written = False

    def __enter__(self) -> "Writer":
        self._fh = self._path.open("wb")
        self._write_text_header()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh:
            self._fh.close()
        self._fh = None
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
            "",
        ]
        for line in lines:
            self._fh.write(line.encode("ascii") + b"\n")
        self._header_written = True

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        self._fh.write(tag)
        self._fh.write(struct.pack("<I", len(payload)))
        if payload:
            self._fh.write(payload)
