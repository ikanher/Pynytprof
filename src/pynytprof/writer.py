from __future__ import annotations

import os
import struct
import time
from pathlib import Path
from hashlib import sha1
import zlib

__all__ = ["Writer"]

TAG_T = b"T"

PREFIX = b"NYTPROF\0"
VERSION = 5


class _StringTable:
    def __init__(self) -> None:
        self._strings: dict[str, int] = {}

    def add(self, s: str) -> int:
        if s not in self._strings:
            self._strings[s] = len(self._strings)
        return self._strings[s]

    def serialize(self) -> bytes:
        out = bytearray()
        out.extend(struct.pack("<I", len(self._strings)))
        for s in self._strings:
            b = s.encode("utf-8")
            out.extend(struct.pack("<I", len(b)))
            out.extend(b)
        return bytes(out)


class Writer:
    """Minimal NYTProf file writer used for tests."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._fh: os.PathLike | None = None
        self._header_written = False
        self._header_bytes = b""
        self._compressed_used = False
        self._table = _StringTable()
        self._table_written = False
        self._file_id_counter = 0
        self._file_count = 0
        self._start_ns = 0
        self._stmts: dict[int, dict[int, list[int]]] = {}

    def _compress(self, tag: bytes, data: bytes) -> bytes:
        if not data:
            return data
        if tag in {b"F", b"D", b"C", b"S"}:
            self._compressed_used = True
            return zlib.compress(data, 6)
        if tag == TAG_T and len(data) > 1024:
            self._compressed_used = True
            return zlib.compress(data, 6)
        return data

    def _next_file_id(self) -> int:
        fid = self._file_id_counter
        self._file_id_counter += 1
        return fid

    def _file_record(self, path: str, is_main: bool) -> bytes:
        path_idx = self._table.add(path)
        try:
            digest = sha1(Path(path).read_bytes()).hexdigest()
        except OSError:
            digest = "0" * 40
        digest_idx = self._table.add(digest)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        flags = 1 if is_main else 0
        self._file_count += 1
        return struct.pack(
            "<IIIII",
            self._next_file_id(),
            path_idx,
            digest_idx,
            size,
            flags,
        )

    def _rewrite_header(self) -> None:
        data = self._path.read_bytes()
        rest = data[len(self._header_bytes) :]
        lines = self._header_bytes.rstrip(b"\n").split(b"\n")
        if lines and lines[-1] == b"":
            lines = lines[:-1]
        if self._compressed_used and b"compressed=1" not in lines:
            lines.append(b"compressed=1")
        if b"has_stmt=1" not in lines:
            lines.append(b"has_stmt=1")
        lines.append(b"has_end=1")
        lines.append(f"filecount={self._file_count}".encode("ascii"))
        lines.append(b"stringtable=present")
        lines.append(f"stringcount={len(self._table._strings)}".encode("ascii"))
        lines.append(b"")
        new_header = b"\n".join(lines) + b"\n"
        self._path.write_bytes(new_header + rest)
        self._header_bytes = new_header

    def __enter__(self) -> "Writer":
        self._fh = self._path.open("wb")
        self._start_ns = time.time_ns()
        self._write_text_header()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._fh:
            if not self._table_written:
                self._write_chunk(TAG_T, self._table.serialize())
                self._table_written = True
            for fid in list(self._stmts):
                self._flush_statement_file(fid)
            end_ns = time.time_ns() - self._start_ns
            self._write_chunk(b"E", struct.pack("<Q", end_ns))
            self._fh.close()
        self._fh = None
        self._rewrite_header()
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
            "has_stmt=1",
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

    def _ensure_table(self) -> None:
        if not self._table_written:
            self._write_chunk(TAG_T, self._table.serialize())
            self._table_written = True

    def _write_file_chunk(self, records: list[tuple[str, bool]]) -> None:
        self._ensure_table()
        payload = bytearray()
        for path, is_main in records:
            payload.extend(self._file_record(path, is_main))
        self._write_chunk(b"F", bytes(payload))

    def _write_sub_chunk(self, records: list[tuple[int, int, int, int, str]]) -> None:
        self._ensure_table()
        payload = bytearray()
        for sid, fid, sl, el, name in records:
            payload.extend(struct.pack("<IIII", sid, fid, sl, el))
            idx = self._table.add(name)
            payload.extend(struct.pack("<I", idx))
        self._write_chunk(b"D", bytes(payload))

    _stmt_struct = struct.Struct("<IIIQ")

    def _flush_statement_block(self, records: list[tuple[int, int, int, int]]) -> None:
        payload = bytearray(len(records) * self._stmt_struct.size)
        off = 0
        for rec in records:
            self._stmt_struct.pack_into(payload, off, *rec)
            off += self._stmt_struct.size
        self._write_chunk(b"D", bytes(payload))

    def _flush_statement_file(self, fid: int) -> None:
        recs = self._stmts.get(fid)
        if not recs:
            return
        packed = [(fid, line, vals[0], vals[1]) for line, vals in sorted(recs.items())]
        self._flush_statement_block(packed)
        self._stmts[fid] = {}

    def record_statement(self, fid: int, line: int, elapsed_ns: int | None) -> None:
        data = self._stmts.setdefault(fid, {})
        hit_time = data.get(line)
        if hit_time is None:
            hit_time = [0, 0]
            data[line] = hit_time
        if hit_time[0] < 0xFFFF_FFFF:
            hit_time[0] = min(0xFFFF_FFFF, hit_time[0] + 1)
        if elapsed_ns is not None:
            hit_time[1] += elapsed_ns
        if len(data) >= 8000:
            self._flush_statement_file(fid)
