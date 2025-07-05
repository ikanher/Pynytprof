# Simple pure-Python NYTProf writer fallback
from __future__ import annotations

from pathlib import Path
import struct


HDR = b"NYTPROF\0" + struct.pack("<II", 5, 0)
H_CHUNK = b"H" + struct.pack("<I", 8) + struct.pack("<II", 5, 0)


def _chunk(tok: bytes, payload: bytes) -> bytes:
    return tok + struct.pack("<I", len(payload)) + payload


def write(
    out_path: str,
    files: list[tuple[int, int, int, int, str]],
    defs: list[tuple[int, int, int, int, str]],
    calls: list[tuple[int, int, int, int, int]],
    lines: list[tuple[int, int, int, int, int]],
    start_ns: int,
    ticks_per_sec: int,
) -> None:
    """Write NYTProf file purely in Python."""
    path = Path(out_path)
    with path.open("wb") as f:
        f.write(HDR)
        f.write(H_CHUNK)
        a_payload = f"ticks_per_sec={ticks_per_sec}\0start_time={start_ns}\0".encode()
        f.write(_chunk(b"A", a_payload))
        f_payload = b"".join(
            struct.pack("<IIII", fid, flags, size, mtime) + p.encode() + b"\0"
            for fid, flags, size, mtime, p in files
        )
        f.write(_chunk(b"F", f_payload))
        d_payload = b"".join(
            struct.pack("<IIII", sid, fid, sl, el) + name.encode() + b"\0"
            for sid, fid, sl, el, name in defs
        )
        f.write(_chunk(b"D", d_payload))
        c_payload = b"".join(
            struct.pack("<IIIQQ", fid, line, sid, inc // 100, exc // 100)
            for fid, line, sid, inc, exc in calls
        )
        f.write(_chunk(b"C", c_payload))
        s_payload = b"".join(
            struct.pack("<IIIQQ", fid, line, calls_v, inc // 100, exc // 100)
            for fid, line, calls_v, inc, exc in lines
        )
        f.write(_chunk(b"S", s_payload))
        f.write(_chunk(b"E", b""))


