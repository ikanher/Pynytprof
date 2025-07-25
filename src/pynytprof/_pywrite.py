from __future__ import annotations

from pathlib import Path
import struct
import time
import os
import sys
import platform
import datetime
from email.utils import format_datetime
from importlib import resources
import re

try:  # Python 3.9+
    _version_text = resources.files(__package__).joinpath("nytp_version.h").read_text()
except AttributeError:  # pragma: no cover - fallback for Python < 3.9
    _version_text = resources.read_text(__package__, "nytp_version.h")
_major_match = re.search(r"NYTPROF_MAJOR\s+(\d+)", _version_text)
_minor_match = re.search(r"NYTPROF_MINOR\s+(\d+)", _version_text)
NYTPROF_MAJOR = int(_major_match.group(1)) if _major_match else 5
NYTPROF_MINOR = int(_minor_match.group(1)) if _minor_match else 0


def _make_ascii_header(static: str) -> bytes:
    """Return the finalized banner bytes with exactly one trailing LF."""
    banner = static.rstrip("\n") + "\n"
    return banner.encode()


def _chunk(tok: bytes, payload: bytes) -> bytes:
    return tok[:1] + len(payload).to_bytes(4, "little") + payload


def _debug_write(fh, data: bytes) -> None:
    if os.getenv("PYNYTPROF_DEBUG"):
        print(f"DEBUG: about to write raw data of length={len(data)}", file=sys.stderr)
    fh.write(data)


class Writer:
    def __init__(
        self,
        path: str | None = None,
        start_ns: int | None = None,
        ticks_per_sec: int = 10_000_000,
        tracer=None,
        script_path: str | None = None,
        fp=None,
        *,
        outer_chunks: bool | None = None,
    ) -> None:
        self._path = Path(path) if path is not None else None
        self._fh = fp
        self.start_time = time.time_ns() if start_ns is None else start_ns
        self.ticks_per_sec = ticks_per_sec
        self._start_ns = self.start_time
        self.tracer = tracer
        self.writer = self
        self.script_path = str(Path(script_path or sys.argv[0]).resolve())
        self._line_hits: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._stmt_records: list[tuple[int, int, int]] = []
        self._payloads: dict[bytes, bytearray] = {
            b"F": bytearray(),
            b"S": bytearray(),
            b"D": bytearray(),
            b"C": bytearray(),
        }
        self.nv_size = struct.calcsize("d")
        self._file_ids: dict[str, int] = {}
        self._next_fid = 1
        self._register_file(self.script_path)
        self._strings: dict[str, int] = {}
        self._offset = 0
        if outer_chunks is None:
            outer_chunks = os.getenv("PYNYTPROF_OUTER_CHUNKS", "0") == "1"
        self.outer_chunks = bool(outer_chunks)
        if os.getenv("PYNYTPROF_DEBUG"):
            print(
                f"DEBUG: Writer initialized with empty buffers; outer_chunks={self.outer_chunks}",
                file=sys.stderr,
            )

    def _string_index(self, s: str) -> int:
        idx = self._strings.get(s)
        if idx is None:
            idx = len(self._strings)
            self._strings[s] = idx
        return idx

    def _register_file(self, pathname: str) -> int:
        fid = self._file_ids.get(pathname)
        if fid is None:
            fid = self._next_fid
            self._file_ids[pathname] = fid
            self._next_fid += 1
        return fid

    def _write_raw_P(
        self, pid: int | None = None, ppid: int | None = None, tstamp: float | None = None
    ) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        if pid is None:
            pid = os.getpid()
        if ppid is None:
            ppid = os.getppid()
        if tstamp is None:
            tstamp = time.time()
        assert self.nv_size == struct.calcsize("d")
        payload = (
            struct.pack("<I", pid)
            + struct.pack("<I", ppid)
            + struct.pack("<d", tstamp)
        )
        _debug_write(self._fh, b"P")
        _debug_write(self._fh, payload)
        self._offset += 1 + len(payload)

    def _emit_new_fid(
        self,
        fid: int,
        eval_fid: int,
        eval_line_num: int,
        flags: int,
        size: int,
        mtime: int,
        name: bytes,
        utf8: bool = False,
    ) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")

        from .protocol import write_tag_u32, write_u32, output_str
        from .tags import NYTP_TAG_NEW_FID

        payload = bytearray()
        payload += write_tag_u32(NYTP_TAG_NEW_FID, fid)
        payload += write_u32(eval_fid)
        payload += write_u32(eval_line_num)
        payload += write_u32(flags)
        payload += write_u32(size)
        payload += write_u32(mtime)
        payload += output_str(name, utf8)

        _debug_write(self._fh, bytes(payload))
        self._offset += len(payload)

    def _write_F_chunk(self) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = b"".join(
            struct.pack("<II", fid, self._string_index(path))
            for path, fid in sorted(self._file_ids.items(), key=lambda x: x[1])
        )
        self._write_chunk(b"F", payload)
        self._offset += (5 if self.outer_chunks else 0) + len(payload)
        self._payloads[b"F"] = bytearray()

    def _write_header(self) -> None:
        timestamp = format_datetime(datetime.datetime.now(datetime.timezone.utc))
        basetime = int(self._start_ns // 1_000_000_000)
        script = os.path.basename(self.script_path)

        lines = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}".encode(),
            f"#Perl profile database. Generated by Pynytprof on {timestamp}".encode(),
            f":basetime={basetime}".encode(),
            f":application={script}".encode(),
            f":perl_version={sys.version.split()[0]}".encode(),
            f":nv_size={self.nv_size}".encode(),
            b":xs_version=6.11",
            b":PL_perldb=0",
            b":clock_id=1",
            b":ticks_per_sec=10000000",
            b"!usecputime=0",
            b"!subs=1",
            b"!blocks=0",
            b"!leave=1",
            b"!expand=0",
            b"!trace=0",
            b"!use_db_sub=0",
            b"!compress=0",
            b"!clock=1",
            b"!stmts=1",
            b"!slowops=2",
            b"!findcaller=0",
            b"!forkdepth=-1",
            b"!perldb=0",
            b"!nameevals=1",
            b"!nameanonsubs=1",
            b"!calls=1",
            b"!evals=0",
        ]

        banner = b"\n".join(lines).rstrip(b"\n") + b"\n"
        if os.getenv("PYNYTPROF_DEBUG"):
            last_line = banner.rstrip(b"\n").split(b"\n")[-1] + b"\n"
            print(f"DEBUG: writing banner len={len(banner)}", file=sys.stderr)
            print(f"DEBUG: banner_end={last_line!r}", file=sys.stderr)

        self._fh.write(banner)
        self._offset = len(banner)

        self._write_raw_P()
        first_token_offset = self._offset
        self._emit_new_fid(
            fid=1,
            eval_fid=0,
            eval_line_num=0,
            flags=0,
            size=0,
            mtime=0,
            name=b"(unknown)",
            utf8=False,
        )
        if os.getenv("PYNYTPROF_DEBUG"):
            expected_stream_off = len(banner) + 1 + 4 + 4 + self.nv_size
            print("DEBUG: wrote raw P record (17 B)", file=sys.stderr)
            print(
                f"DEBUG: first_token_offset={first_token_offset}",
                file=sys.stderr,
            )
            print(
                f"DEBUG: header_len={len(banner)} nv_size={self.nv_size} expected_stream_off={expected_stream_off}",
                file=sys.stderr,
            )

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        assert len(tag) == 1
        if self._fh is None:
            raise ValueError("writer not opened")
        if os.getenv("PYNYTPROF_DEBUG"):
            offset = self._fh.tell()
            from hashlib import sha256

            digest = sha256(payload).hexdigest() if payload else ""
            first16 = payload[:16].hex()
            last16 = payload[-16:].hex() if payload else ""
            print(
                f"DEBUG: write tag={tag.decode()} len={len(payload)}",
                file=sys.stderr,
            )
            print(
                f"       offset=0x{offset:x}",
                file=sys.stderr,
            )
            print(
                f"       sha256={digest}",
                file=sys.stderr,
            )
            if payload:
                print(
                    f"       first16={first16} last16={last16}",
                    file=sys.stderr,
                )
        if self.outer_chunks:
            _debug_write(self._fh, tag)
            _debug_write(self._fh, struct.pack("<I", len(payload)))
        else:
            if os.getenv("PYNYTPROF_DEBUG"):
                print(
                    "DEBUG: outer_chunks=False -> emitting payload only",
                    file=sys.stderr,
                )
        if payload:
            _debug_write(self._fh, payload)

    def record_line(self, fid: int, line: int, calls: int, inc: int, exc: int) -> None:
        self._line_hits[(fid, line)] = (calls, inc, exc)

    def write_chunk(self, token: bytes, payload: bytes) -> None:
        tag = token[:1]
        if tag in self._payloads:
            if tag == b"D" and not payload:
                return
            self._payloads[tag].extend(payload)
        elif tag == b"E":
            pass

    def __enter__(self):
        if self._fh is None:
            if self._path is None:
                raise ValueError("no output path specified")
            self._fh = open(self._path, "wb")
        self._write_header()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.finalize()

    def close(self) -> None:
        if not self._fh:
            return

        self._register_file(self.script_path)

        if self.tracer is not None:

            def ns2ticks(ns: int) -> int:
                return ns // 100

            for line, calls in self.tracer._line_hits.items():
                self._line_hits[(0, line)] = (
                    calls,
                    ns2ticks(self.tracer._line_time_ns[line]),
                    ns2ticks(self.tracer._exc_time_ns.get(line, 0)),
                )

        recs = []
        for (fid, line), (calls, inc, exc) in self._line_hits.items():
            recs.append(struct.pack("<IIIQQ", fid, line, calls, inc, exc))
        if recs:
            self._payloads[b"S"].extend(b"".join(recs))

        if self._stmt_records and not self._payloads[b"D"]:
            buf = bytearray()
            for fid, line, dur in self._stmt_records:
                buf += struct.pack("<BIIQ", 1, fid, line, dur)
            buf.append(0)
            self._payloads[b"D"] = buf
        elif not self._payloads[b"D"]:
            self._payloads[b"D"] = bytearray()

        if os.getenv("PYNYTPROF_DEBUG"):
            summary = {t.decode(): len(self._payloads.get(t, b"")) for t in [b"S", b"F", b"D", b"C"]}
            summary["E"] = 0
            print(f"FINAL CHUNKS: {summary}", file=sys.stderr)

        # emit S chunk first
        s_payload = bytes(self._payloads.get(b"S", b""))
        self._write_chunk(b"S", s_payload)
        self._offset += (5 if self.outer_chunks else 0) + len(s_payload)

        # emit F chunk built from registered files
        if self._file_ids and not self._payloads[b"F"]:
            self._write_F_chunk()
        else:
            f_payload = bytes(self._payloads.get(b"F", b""))
            self._write_chunk(b"F", f_payload)
            self._offset += (5 if self.outer_chunks else 0) + len(f_payload)

        for tag in [b"D", b"C"]:
            payload = bytes(self._payloads.get(tag, b""))
            self._write_chunk(tag, payload)
            self._offset += (5 if self.outer_chunks else 0) + len(payload)

        # final end marker is only written when outer_chunks=True
        if self.outer_chunks:
            _debug_write(self._fh, b"E")
            self._offset += 1
        self._fh.close()
        self._fh = None

    def finalize(self) -> None:
        self.close()


def write(out_path: str, files, defs, calls, lines, start_ns: int, ticks_per_sec: int) -> None:
    path = Path(out_path)
    with path.open("wb") as f:
        timestamp = format_datetime(datetime.datetime.now(datetime.timezone.utc))
        basetime = int(start_ns // 1_000_000_000)
        try:
            hz = os.sysconf("SC_CLK_TCK")
        except (AttributeError, ValueError, OSError):
            hz = 100

        lines_hdr = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}".encode(),
            f"#Perl profile database. Generated by Pynytprof on {timestamp}".encode(),
            f":basetime={basetime}".encode(),
            b":application=-e",
            f":perl_version={sys.version.split()[0]}".encode(),
            f":nv_size={struct.calcsize('d')}".encode(),
            b":xs_version=6.11",
            b":PL_perldb=0",
            b":clock_id=1",
            b":ticks_per_sec=10000000",
            b"!usecputime=0",
            b"!subs=1",
            b"!blocks=0",
            b"!leave=1",
            b"!expand=0",
            b"!trace=0",
            b"!use_db_sub=0",
            b"!compress=0",
            b"!clock=1",
            b"!stmts=1",
            b"!slowops=2",
            b"!findcaller=0",
            b"!forkdepth=-1",
            b"!perldb=0",
            b"!nameevals=1",
            b"!nameanonsubs=1",
            b"!calls=1",
            b"!evals=0",
        ]

        banner = b"\n".join(lines_hdr).rstrip(b"\n") + b"\n"

        f.write(banner)

        pid = os.getpid()
        ppid = os.getppid()
        tstamp = time.time()
        payload = struct.pack("<I", pid) + struct.pack("<I", ppid) + struct.pack("<d", tstamp)
        assert len(payload) == 16
        f.write(b"P")
        f.write(payload)

        s_payload = b"".join(
            struct.pack("<IIIQQ", fid, line, calls_v, inc // 100, exc // 100)
            for fid, line, calls_v, inc, exc in lines
        )
        f.write(_chunk(b"S", s_payload))

        d_payload = b""
        c_payload = b""
        if defs:
            if len(defs[0]) == 3:
                d_payload = b"".join(
                    struct.pack("<II", sid, flags) + name.encode() + b"\0"
                    for sid, flags, name in defs
                )
                c_payload = b"".join(
                    struct.pack("<IIIQQ", cs, ce, cnt, t, st) for cs, ce, cnt, t, st in calls
                )
            else:
                d_payload = b"".join(
                    struct.pack("<IIII", sid, fid, sl, el) + name.encode() + b"\0"
                    for sid, fid, sl, el, name in defs
                )
                c_payload = b"".join(
                    struct.pack("<IIIQQ", fid, line, sid, inc // 100, exc // 100)
                    for fid, line, sid, inc, exc in calls
                )
        f.write(_chunk(b"D", d_payload))
        f.write(_chunk(b"C", c_payload))
        f.write(_chunk(b"E", b""))
