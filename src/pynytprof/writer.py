from __future__ import annotations

import os
import struct
import time
import sys
import platform
from pathlib import Path
from hashlib import sha1
import zlib

__all__ = ["Writer"]

TAG_T = b"T"

_MAJOR = 5
_MINOR = 0
_MAGIC = f"NYTProf {_MAJOR} {_MINOR}\n".encode()


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


class _SubTable:
    def __init__(self, tbl: _StringTable) -> None:
        self._tbl = tbl
        self._records: list[tuple[int, int, int, int, int, int]] = []
        self._sub_id_counter = 0

    def add(self, file_id: int, start: int, end: int, name: str, pkg: str) -> int:
        sub_id = self._sub_id_counter
        self._sub_id_counter += 1
        name_idx = self._tbl.add(name)
        pkg_idx = self._tbl.add(pkg)
        self._records.append((sub_id, file_id, start, end, name_idx, pkg_idx))
        return sub_id

    def serialize(self) -> bytes:
        if not self._records:
            return b""
        st = struct.Struct("<IIIIII")
        payload = bytearray(len(self._records) * st.size)
        off = 0
        for rec in self._records:
            st.pack_into(payload, off, *rec)
            off += st.size
        return bytes(payload)

    @property
    def count(self) -> int:
        return len(self._records)


class _CallGraph:
    def __init__(self) -> None:
        self._edges: dict[tuple[int, int], list[int]] = {}

    def add(self, caller_sid: int, callee_sid: int, dur_ns: int) -> None:
        key = (caller_sid, callee_sid)
        rec = self._edges.get(key)
        if rec is None:
            self._edges[key] = [1, dur_ns]
        else:
            if rec[0] < 0xFFFF_FFFF:
                rec[0] = min(0xFFFF_FFFF, rec[0] + 1)
            rec[1] += dur_ns

    def serialize(self) -> bytes:
        if not self._edges:
            return b""
        st = struct.Struct("<IIIQQ")
        payload = bytearray(len(self._edges) * st.size)
        off = 0
        for (caller, callee), (count, dur) in self._edges.items():
            ticks = dur
            st.pack_into(payload, off, caller, callee, count, ticks, ticks)
            off += st.size
        length = len(payload)
        assert length % st.size == 0
        return bytes(payload)

    def __len__(self) -> int:  # pragma: no cover - simple
        return len(self._edges)


class _SubStats:
    def __init__(self) -> None:
        self.calls = 0
        self.incl_ns = 0
        self.child_ns = 0

    def update(self, time_ns: int, child_time_ns: int) -> None:
        if self.calls < 0xFFFF_FFFF:
            self.calls = min(0xFFFF_FFFF, self.calls + 1)
        self.incl_ns += time_ns
        self.child_ns += child_time_ns

    @property
    def excl_ns(self) -> int:
        return self.incl_ns - self.child_ns


class Writer:
    """Minimal NYTProf file writer used for tests."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._fh: os.PathLike | None = None
        self._header_written = False
        self._compressed_used = False
        self._ticks_per_sec = 1_000_000_000
        self._start_time = 0
        self._table = _StringTable()
        self._sub_table = _SubTable(self._table)
        self._callgraph = _CallGraph()
        self._table_written = False
        self._file_id_counter = 0
        self._start_ns = 0
        self._stmts: dict[int, dict[int, list[int]]] = {}
        self._file_records: list[bytes] = []
        self._file_map: dict[str, int] = {}
        self.stats: dict[int, _SubStats] = {}
        if os.getenv("PYNYTPROF_DEBUG"):
            print("DEBUG: Writer initialized with empty buffers", file=sys.stderr)

    @property
    def sub_table(self) -> _SubTable:
        return self._sub_table

    @property
    def callgraph(self) -> _CallGraph:
        return self._callgraph

    @property
    def stats_map(self) -> dict[int, _SubStats]:
        return self.stats

    def add_file(self, path: str, is_main: bool = False) -> int:
        fid = self._file_map.get(path)
        if fid is not None:
            return fid
        rec = self._file_record(path, is_main)
        fid = struct.unpack_from("<I", rec)[0]
        self._file_records.append(rec)
        self._file_map[path] = fid
        return fid

    def _compress(self, tag: bytes, data: bytes) -> bytes:
        if not data:
            return data
        if tag in {b"F", b"D", b"C", b"S", b"A"}:
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
        return struct.pack(
            "<IIIII",
            self._next_file_id(),
            path_idx,
            digest_idx,
            size,
            flags,
        )

    def __enter__(self) -> "Writer":
        self._fh = self._path.open("wb")
        self._start_ns = time.time_ns()
        self._start_time = time.time()
        self._write_header()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._fh:
            if not self._table_written:
                payload = self._table.serialize()
                if os.getenv("PYNYTPROF_DEBUG"):
                    import sys

                    print(
                        f"DEBUG: emitting chunk tag={TAG_T.decode()} len={len(payload)}",
                        file=sys.stderr,
                    )
                self._write_chunk(TAG_T, payload)
                self._table_written = True
            if self._file_records:
                payload = b"".join(self._file_records)
                if os.getenv("PYNYTPROF_DEBUG"):
                    import sys

                    print(f"DEBUG: emitting chunk tag=F len={len(payload)}", file=sys.stderr)
                self._write_chunk(b"F", payload)
                self._file_records.clear()
            for fid in list(self._stmts):
                self._flush_statement_file(fid)
            if self._sub_table.count:
                payload = self._sub_table.serialize()
                if os.getenv("PYNYTPROF_DEBUG"):
                    import sys

                    print(f"DEBUG: emitting chunk tag=S len={len(payload)}", file=sys.stderr)
                self._write_chunk(b"S", payload)
            if len(self._callgraph):
                payload = self._callgraph.serialize()
                if os.getenv("PYNYTPROF_DEBUG"):
                    import sys

                    print(f"DEBUG: emitting chunk tag=C len={len(payload)}", file=sys.stderr)
                self._write_chunk(b"C", payload)
            if self.stats:
                payload = b"".join(
                    struct.pack("<IIQQI", sid, s.calls, s.incl_ns, s.excl_ns, 0)
                    for sid, s in self.stats.items()
                )
                if os.getenv("PYNYTPROF_DEBUG"):
                    import sys

                    print(f"DEBUG: emitting chunk tag=A len={len(payload)}", file=sys.stderr)
                self._write_chunk(b"A", payload)
            end_ns = time.time_ns() - self._start_ns
            payload = struct.pack("<Q", end_ns)
            if os.getenv("PYNYTPROF_DEBUG"):
                import sys

                print(f"DEBUG: emitting chunk tag=E len={len(payload)}", file=sys.stderr)
            self._write_chunk(b"E", payload)
            self._fh.close()
            if os.getenv("PYNYTPROF_DEBUG"):
                import sys

                print("DEBUG: all chunks emitted", file=sys.stderr)
        self._fh = None

    def _build_attrs(self) -> bytes:
        lines = [
            f"file={self._path}",
            "version=5",
            f"ticks_per_sec={self._ticks_per_sec}",
            f"start_time={int(self._start_time)}",
        ]
        if self._compressed_used:
            lines.append("compressed=1")
        return ("\n".join(lines) + "\n\n").encode("ascii")

    def _write_header(self) -> None:
        try:
            hz = os.sysconf("SC_CLK_TCK")
        except (AttributeError, ValueError, OSError):
            hz = 100
        lines = [
            f"NYTProf {_MAJOR} {_MINOR}",
            f"#Perl profile database. Generated by Pynytprof on "
            f"{time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime())}",
            f":basetime={int(self._start_ns // 1_000_000_000)}",
            ":application=-e",
            f":perl_version={sys.version.split()[0]}",
            f":nv_size={struct.calcsize('d')}",
            ":clock_mod=cpu",
            ":ticks_per_sec=10000000",
            f":osname={platform.system().lower()}",
            f":hz={hz}",
        ]
        banner = "\n".join(lines).rstrip("\n") + "\n"
        assert "\0" not in banner
        data = banner.encode()
        if os.getenv("PYNYTPROF_DEBUG"):
            print(f"DEBUG: about to write raw data of length={len(data)}", file=sys.stderr)
        self._fh.write(data)
        self._header_written = True

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = self._compress(tag, payload)
        data = tag
        if os.getenv("PYNYTPROF_DEBUG"):
            print(f"DEBUG: about to write raw data of length={len(data)}", file=sys.stderr)
        self._fh.write(data)
        data = struct.pack("<I", len(payload))
        if os.getenv("PYNYTPROF_DEBUG"):
            print(f"DEBUG: about to write raw data of length={len(data)}", file=sys.stderr)
        self._fh.write(data)
        if payload:
            data = payload
            if os.getenv("PYNYTPROF_DEBUG"):
                print(f"DEBUG: about to write raw data of length={len(data)}", file=sys.stderr)
            self._fh.write(data)

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
