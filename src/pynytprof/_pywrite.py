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
    """Return the finalized banner bytes."""
    banner = static
    if not banner.endswith("\n"):
        banner += "\n"
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
        self._file_ids: dict[str, int] = {}
        self._next_fid = 1
        self._register_file(self.script_path)
        self._strings: dict[str, int] = {}
        self._offset = 0
        if os.getenv("PYNYTPROF_DEBUG"):
            print("DEBUG: Writer initialized with empty buffers", file=sys.stderr)

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
        payload = (
            struct.pack("<I", pid)
            + struct.pack("<I", ppid)
            + struct.pack("<d", tstamp)
        )
        _debug_write(self._fh, b"P")
        _debug_write(self._fh, payload)
        self._offset += 1 + len(payload)

    def _write_F_chunk(self) -> None:
        if self._fh is None:
            raise ValueError("writer not opened")
        payload = b"".join(
            struct.pack("<II", fid, self._string_index(path))
            for path, fid in sorted(self._file_ids.items(), key=lambda x: x[1])
        )
        self._write_chunk(b"F", payload)
        self._offset += 5 + len(payload)
        self._payloads[b"F"] = bytearray()

    def _write_header(self) -> None:
        timestamp = format_datetime(datetime.datetime.utcnow())
        basetime = int(self._start_ns // 1_000_000_000)
        try:
            hz = os.sysconf("SC_CLK_TCK")  # type: ignore[arg-type]
        except (AttributeError, ValueError, OSError):
            hz = 100
        lines = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}",
            f"#Perl profile database. Generated by Pynytprof on {timestamp}",
            f":basetime={basetime}",
            ":nv_size=8",
            ":application=-e",
            f":perl_version={sys.version.split()[0]}",
            ":clock_mod=cpu",
            ":ticks_per_sec=10000000",
            f":osname={platform.system().lower()}",
            f":hz={hz}",
            "!subs=1",
            "!blocks=0",
            "!leave=1",
            "!expand=0",
            "!trace=0",
            "!use_db_sub=0",
            "!compress=0",
            "!clock=1",
            "!stmts=1",
            "!slowops=2",
            "!findcaller=0",
            "!forkdepth=-1",
            "!perldb=0",
            "!nameevals=1",
            "!nameanonsubs=1",
            "!calls=1",
            "!evals=0",
        ]
        static_banner = "\n".join(lines) + "\n"

        banner = static_banner.encode()
        if os.getenv("PYNYTPROF_DEBUG"):
            last_line = banner.rstrip(b"\n").split(b"\n")[-1] + b"\n"
            print(f"DEBUG: writing banner len={len(banner)}", file=sys.stderr)
            print(f"DEBUG: banner_end={last_line!r}", file=sys.stderr)

        self._fh.write(banner)
        self._offset = len(banner)

        self._write_raw_P()
        if os.getenv("PYNYTPROF_DEBUG"):
            print("DEBUG: wrote raw P record (17 B)", file=sys.stderr)

    def _write_chunk(self, tag: bytes, payload: bytes) -> None:
        payload = payload.replace(b"\n", b"\x01")
        length = len(payload)
        lb = length.to_bytes(4, "little")
        while b"\n" in lb:
            payload += b"\x00"
            length += 1
            lb = length.to_bytes(4, "little")
        if tag in (b"S", b"C"):
            rec_size = struct.calcsize("<IIIQQ")
            rem = length % rec_size
            if rem:
                pad = rec_size - rem
                payload += b"\x00" * pad
                length += pad
                lb = length.to_bytes(4, "little")
        if os.getenv("PYNYTPROF_DEBUG"):
            offset = self._fh.tell()
            from hashlib import sha256

            digest = sha256(payload).hexdigest() if payload else ""
            first16 = payload[:16].hex()
            last16 = payload[-16:].hex() if payload else ""
            print(
                f"DEBUG: write tag={tag.decode()} len={length}",
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
        _debug_write(self._fh, tag)
        _debug_write(self._fh, length.to_bytes(4, "little"))
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

        # final end marker is a raw byte with no length
        _debug_write(self._fh, b"E")
        self._offset += 1
        self._fh.close()
        self._fh = None

    def finalize(self) -> None:
        self.close()


def write(out_path: str, files, defs, calls, lines, start_ns: int, ticks_per_sec: int) -> None:
    path = Path(out_path)
    with path.open("wb") as f:
        try:
            hz = os.sysconf("SC_CLK_TCK")  # type: ignore[arg-type]
        except (AttributeError, ValueError, OSError):
            hz = 100
        lines_hdr = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}",
            "#Perl profile database. Generated by Pynytprof on "
            + time.strftime("%a, %d %b %Y %H:%M:%S %z", time.gmtime()),
            f":basetime={int(start_ns // 1_000_000_000)}",
            ":application=-e",
            f":perl_version={sys.version.split()[0]}",
            ":nv_size=8",
            ":clock_mod=cpu",
            ":ticks_per_sec=10000000",
            f":osname={platform.system().lower()}",
            f":hz={hz}",
            "!subs=1",
            "!blocks=0",
            "!leave=1",
            "!expand=0",
            "!trace=0",
            "!use_db_sub=0",
            "!compress=0",
            "!clock=1",
            "!stmts=1",
            "!slowops=2",
            "!findcaller=0",
            "!forkdepth=-1",
            "!perldb=0",
            "!nameevals=1",
            "!nameanonsubs=1",
            "!calls=1",
            "!evals=0",
        ]
        timestamp = format_datetime(datetime.datetime.utcnow())
        basetime = int(start_ns // 1_000_000_000)
        try:
            hz = os.sysconf("SC_CLK_TCK")
        except (AttributeError, ValueError, OSError):
            hz = 100

        lines_hdr = [
            f"NYTProf {NYTPROF_MAJOR} {NYTPROF_MINOR}",
            f"#Perl profile database. Generated by Pynytprof on {timestamp}",
            f":basetime={basetime}",
            ":nv_size=8",
            ":application=-e",
            f":perl_version={sys.version.split()[0]}",
            ":clock_mod=cpu",
            ":ticks_per_sec=10000000",
            f":osname={platform.system().lower()}",
            f":hz={hz}",
            "!subs=1",
            "!blocks=0",
            "!leave=1",
            "!expand=0",
            "!trace=0",
            "!use_db_sub=0",
            "!compress=0",
            "!clock=1",
            "!stmts=1",
            "!slowops=2",
            "!findcaller=0",
            "!forkdepth=-1",
            "!perldb=0",
            "!nameevals=1",
            "!nameanonsubs=1",
            "!calls=1",
            "!evals=0",
        ]

        static = "\n".join(lines_hdr) + "\n"
        banner = static

        f.write(banner.encode())

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
