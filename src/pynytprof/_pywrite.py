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

from .nytp_stream import (
    write_process_start,
    write_process_end,
    write_new_fid,
    write_src_line,
    write_time_line,
)

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
        if path is not None and not isinstance(path, (str, os.PathLike)):
            # Allow passing an open file handle as the first argument
            fp = path
            path = None
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
        # token bytes accumulated when tracing
        self._payloads: dict[bytes, bytearray] = {}
        self.nv_size = struct.calcsize("d")
        self._file_ids: dict[str, int] = {}
        self._next_fid = 1
        self._register_file(self.script_path)
        self._strings: dict[str, int] = {}
        self._trace_fp = None
        self._started = False
        if DBG.active:
            log("Writer initialized with empty buffers")
            self._buffer = bytearray()
        else:
            self._buffer = bytearray()

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
        payload = write_process_start(pid, ppid, tstamp)
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)
            buf = self._buffer[-17:]
            pid_v = int.from_bytes(buf[1:5], "little")
            ppid_v = int.from_bytes(buf[5:9], "little")
            ts = struct.unpack("<d", buf[9:17])[0]
            log(f"P-rec  pid={pid_v} ppid={ppid_v} ts={ts}  raw={buf.hex(' ')}")

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

        payload = write_new_fid(
            fid,
            eval_fid,
            eval_line_num,
            flags,
            size,
            mtime,
            name,
            utf8,
        )
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)


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

        self._write_raw_P()
        if DBG.active:
            expected_stream_off = len(banner) + 1 + 4 + 4 + self.nv_size
            log("wrote raw P record (17 B)")
            log(
                f"header_len={len(banner)} nv_size={self.nv_size} expected_stream_off={expected_stream_off}"
            )


    def record_line(self, fid: int, line: int, calls: int, inc: int, exc: int) -> None:
        self._line_hits[(fid, line)] = (calls, inc, exc)

    # ------------------------------------------------------------------
    # Minimal profiling helpers used by tests
    def start_profile(self) -> None:
        """Write the header and initial P record if not already done."""
        if self._fh is None:
            if self._path is None:
                raise ValueError("no output path specified")
            self._fh = open(self._path, "wb")
        if not self._started:
            self._write_header()
            self._started = True

    def add_file(
        self,
        fid: int,
        name: str | bytes,
        size: int,
        mtime: int,
        flags: int,
        eval_fid: int,
        eval_line: int,
    ) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = write_new_fid(
            fid,
            eval_fid,
            eval_line,
            flags,
            size,
            mtime,
            name,
        )
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)

    def add_src_line(self, fid: int, line: int, text: str | bytes) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = write_src_line(fid, line, text)
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)

    def write_time_line(self, fid: int, line: int, elapsed: int, overflow: int) -> None:
        """Emit a minimal time line record (T chunk)."""
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = write_time_line(elapsed, overflow, fid, line)
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)

    def end_profile(self) -> None:
        """Finalize and close the output."""
        self.close()



    def __enter__(self):
        if self._fh is None:
            if self._path is None:
                raise ValueError("no output path specified")
            self._fh = open(self._path, "wb")
        if DBG.active and self._path is not None:
            self._trace_fp = open(str(self._path) + ".trace.txt", "w")
            DBG.extras.append(self._trace_fp)
        if not self._started:
            self._write_header()
            self._started = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.finalize()

    def close(self) -> None:
        if not self._fh:
            return

        end_ts = time.time()
        payload = write_process_end(os.getpid(), end_ts)
        _debug_write(self._fh, payload)
        if DBG.active:
            self._buffer.extend(payload)
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
