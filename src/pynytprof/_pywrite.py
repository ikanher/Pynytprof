from __future__ import annotations

from pathlib import Path
import struct
import time
import os
import sys
import datetime
from email.utils import format_datetime
from importlib import resources
import re

from ._debug import DBG, log, hexdump_around

from .token_writer import TokenWriter

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
    if DBG.active:
        log(f"about to write raw data of length={len(data)}")
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
        self._tok = TokenWriter()
        self._trace_fp = None
        if DBG.active:
            log("Writer initialized with empty buffers")
            self._buffer = bytearray()
            self._chunk_meta: list[tuple[str, int, int]] = []
        else:
            self._buffer = bytearray()
            self._chunk_meta = []

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
        payload = self._tok.write_p_record(pid, ppid, tstamp)
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)
            buf = self._buffer[-17:]
            pid_v = int.from_bytes(buf[1:5], "little")
            ppid_v = int.from_bytes(buf[5:9], "little")
            ts = struct.unpack("<d", buf[9:17])[0]
            log(f"P-rec  pid={pid_v} ppid={ppid_v} ts={ts}  raw={buf.hex(' ')}")
        self._offset += len(payload)

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

        payload = self._tok.write_new_fid(
            fid,
            eval_fid,
            eval_line_num,
            flags,
            size,
            mtime,
            name,
        )
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)
        self._offset += len(payload)

    def _write_F_chunk(self) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        from .protocol import write_u32

        payload = bytearray()
        for path, fid in sorted(self._file_ids.items(), key=lambda x: x[1]):
            payload += write_u32(fid)
            payload += write_u32(self._string_index(path))
        payload = bytes(payload)
        self._write_chunk(b"F", payload)
        self._offset += 5 + len(payload)
        self._payloads[b"F"] = bytearray()

    def _write_header(self) -> None:
        timestamp = format_datetime(datetime.datetime.now(datetime.timezone.utc))
        basetime = int(self._start_ns // 1_000_000_000)
        script = os.path.basename(self.script_path)

        lines = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}".encode("ascii"),
            f"#Perl profile database. Generated by Pynytprof on {timestamp}".encode("ascii"),
            f":basetime={basetime}".encode("ascii"),
            f":application={script}".encode("ascii"),
            f":perl_version={sys.version.split()[0]}".encode("ascii"),
            f":nv_size={self.nv_size}".encode("ascii"),
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
        if DBG.active:
            last_line = banner.rstrip(b"\n").split(b"\n")[-1] + b"\n"
            log(f"writing banner len={len(banner)}")
            log(f"banner_end={last_line!r}")

        _debug_write(self._fh, banner)
        if DBG.active:
            self._buffer.extend(banner)
        self._offset = len(banner)

        self._write_raw_P()
        first_token_offset = self._offset
        if DBG.active:
            expected_stream_off = len(banner) + 1 + 4 + 4 + self.nv_size
            log("wrote raw P record (17 B)")
            log(f"first_token_offset={first_token_offset}")
            log(
                f"header_len={len(banner)} nv_size={self.nv_size} expected_stream_off={expected_stream_off}"
            )

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        assert len(tag) == 1
        if self._fh is None:
            raise ValueError("writer not opened")
        if DBG.active:
            offset = self._fh.tell()
            from hashlib import sha256

            digest = sha256(payload).hexdigest() if payload else ""
            first16 = payload[:16].hex()
            last16 = payload[-16:].hex() if payload else ""
            log(f"write tag={tag.decode()} len={len(payload)}")
            log(f"       offset=0x{offset:x}")
            log(f"       sha256={digest}")
            if payload:
                log(f"       first16={first16} last16={last16}")
                from .protocol import read_u32
                from .tags import KNOWN_TAGS

                dec = []
                off = 0
                limit = min(len(payload), 32)
                while off < limit:
                    tag_byte = payload[off]
                    off += 1
                    if tag_byte not in KNOWN_TAGS:
                        break
                    val, off = read_u32(payload, off)
                    dec.append(f"[tag=0x{tag_byte:02x}, ints=[{val}]]")
                    if off >= limit:
                        break
                if dec:
                    log("       preview=" + " ".join(dec))
        _debug_write(self._fh, tag)
        _debug_write(self._fh, struct.pack("<I", len(payload)))
        if payload:
            _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(tag)
            self._buffer.extend(struct.pack("<I", len(payload)))
            if payload:
                self._buffer.extend(payload)
            self._chunk_meta.append((tag.decode(), self._offset, len(payload)))

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
        if DBG.active and self._path is not None:
            self._trace_fp = open(str(self._path) + ".trace.txt", "w")
            DBG.extras.append(self._trace_fp)
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

        from .protocol import write_u32

        if self._line_hits:
            buf = bytearray()
            for (fid, line), (calls, inc, exc) in self._line_hits.items():
                buf += write_u32(fid)
                buf += write_u32(line)
                buf += write_u32(calls)
                buf += struct.pack("<QQ", inc, exc)
            self._payloads[b"S"].extend(buf)

        if self._stmt_records and not self._payloads[b"D"]:
            from .protocol import write_u32

            buf = bytearray()
            for fid, line, dur in self._stmt_records:
                buf.append(1)
                buf += write_u32(fid)
                buf += write_u32(line)
                buf += struct.pack("<Q", dur)
            buf.append(0)
            self._payloads[b"D"] = buf
        elif not self._payloads[b"D"]:
            self._payloads[b"D"] = bytearray()

        if DBG.active:
            summary = {
                t.decode(): len(self._payloads.get(t, b"")) for t in [b"S", b"F", b"D", b"C"]
            }
            summary["E"] = 0
            log(f"FINAL CHUNKS: {summary}")

        # emit S chunk first
        s_payload = bytes(self._payloads.get(b"S", b""))
        self._write_chunk(b"S", s_payload)
        self._offset += 5 + len(s_payload)

        # emit F chunk built from registered files
        if self._file_ids and not self._payloads[b"F"]:
            self._write_F_chunk()
        else:
            f_payload = bytes(self._payloads.get(b"F", b""))
            self._write_chunk(b"F", f_payload)
            self._offset += 5 + len(f_payload)

        for tag in [b"D", b"C"]:
            payload = bytes(self._payloads.get(tag, b""))
            self._write_chunk(tag, payload)
            self._offset += 5 + len(payload)

        self._write_chunk(b"E", b"")
        self._offset += 5
        if DBG.active:
            log("\nDEBUG  CHUNK  off   len")
            for tag, off, l in self._chunk_meta:
                log(f"      {tag:<2}   0x{off:06x} {l}")
            if DBG.at_off:
                hexdump_around(bytes(self._buffer), DBG.at_off)
        self._fh.close()
        self._fh = None
        if DBG.active and self._trace_fp:
            DBG.extras.remove(self._trace_fp)
            self._trace_fp.close()

    def finalize(self) -> None:
        self.close()


def write(out_path: str, files, defs, calls, lines, start_ns: int, ticks_per_sec: int) -> None:
    path = Path(out_path)
    with path.open("wb") as f:
        timestamp = format_datetime(datetime.datetime.now(datetime.timezone.utc))
        basetime = int(start_ns // 1_000_000_000)
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

        from .protocol import write_u32

        s_payload = bytearray()
        for fid, line, calls_v, inc, exc in lines:
            s_payload += write_u32(fid)
            s_payload += write_u32(line)
            s_payload += write_u32(calls_v)
            s_payload += struct.pack("<QQ", inc // 100, exc // 100)
        s_payload = bytes(s_payload)
        f.write(_chunk(b"S", s_payload))

        d_payload = b""
        c_payload = b""
        if defs:
            if len(defs[0]) == 3:
                d_buf = bytearray()
                for sid, flags, name in defs:
                    d_buf += write_u32(sid)
                    d_buf += write_u32(flags)
                    d_buf += name.encode() + b"\0"
                d_payload = bytes(d_buf)

                c_buf = bytearray()
                for cs, ce, cnt, t, st in calls:
                    c_buf += write_u32(cs)
                    c_buf += write_u32(ce)
                    c_buf += write_u32(cnt)
                    c_buf += struct.pack("<QQ", t, st)
                c_payload = bytes(c_buf)
            else:
                d_buf = bytearray()
                for sid, fid, sl, el, name in defs:
                    d_buf += write_u32(sid)
                    d_buf += write_u32(fid)
                    d_buf += write_u32(sl)
                    d_buf += write_u32(el)
                    d_buf += name.encode() + b"\0"
                d_payload = bytes(d_buf)

                c_buf = bytearray()
                for fid, line, sid, inc, exc in calls:
                    c_buf += write_u32(fid)
                    c_buf += write_u32(line)
                    c_buf += write_u32(sid)
                    c_buf += struct.pack("<QQ", inc // 100, exc // 100)
                c_payload = bytes(c_buf)
        f.write(_chunk(b"D", d_payload))
        f.write(_chunk(b"C", c_payload))
        f.write(_chunk(b"E", b""))
