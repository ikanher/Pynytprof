from __future__ import annotations

import json
import struct
from pathlib import Path
import subprocess
import shutil

__all__ = ["to_html", "to_speedscope"]


def _parse(path: str) -> tuple[dict, dict, dict, list, list]:
    data = Path(path).read_bytes()
    PREFIX = b"NYTPROF\0"
    if data[:8] != PREFIX:
        raise ValueError("bad header")
    if len(data) < 20:
        raise ValueError("truncated header")
    version = struct.unpack_from("<I", data, 8)[0]
    if version != 5:
        raise ValueError("bad version")
    header_len = struct.unpack_from("<Q", data, 12)[0]
    off = 20 + header_len
    attrs: dict[str, int] = {}
    files: dict[int, dict] = {}
    defs: dict[int, dict] = {}
    calls: list[tuple[int, int, int, int, int]] = []
    lines: list[tuple[int, int, int, int, int]] = []
    while off < len(data):
        tok = data[off : off + 1].decode()
        off += 1
        length = struct.unpack_from("<I", data, off)[0]
        off += 4
        payload = data[off : off + length]
        off += length
        if tok == "A":
            attrs = {
                k.decode(): int(v)
                for k, v in (p.split(b"=", 1) for p in payload[:-1].split(b"\0"))
            }
        elif tok == "F":
            p = 0
            while p + 16 <= length:
                fid, flags, size, mt = struct.unpack_from("<IIII", payload, p)
                p += 16
                end = payload.find(b"\0", p)
                files[fid] = {
                    "path": payload[p:end].decode(),
                    "flags": flags,
                    "size": size,
                    "mtime": mt,
                }
                p = end + 1
        elif tok == "D":
            p = 0
            while p + 16 <= length:
                sid, fid, sl, el = struct.unpack_from("<IIII", payload, p)
                p += 16
                end = payload.find(b"\0", p)
                name = payload[p:end].decode()
                defs[sid] = {"fid": fid, "name": name, "sl": sl, "el": el}
                p = end + 1
        elif tok == "C":
            p = 0
            rec_size = 28
            while p + rec_size <= length:
                fid, line, sid, inc, exc = struct.unpack_from("<IIIQQ", payload, p)
                calls.append((fid, line, sid, inc, exc))
                p += rec_size
        elif tok == "S":
            p = 0
            rec_size = 28
            while p + rec_size <= length:
                fid, line, callc, inc, exc = struct.unpack_from("<IIIQQ", payload, p)
                lines.append((fid, line, callc, inc, exc))
                p += rec_size
        elif tok == "E":
            break
    return attrs, files, defs, calls, lines


def to_html(in_path: str, out_dir: str | None = None) -> str:
    dest = out_dir or str(Path(in_path).with_suffix("")) + "_html"
    if shutil.which("nytprofhtml") is None:
        raise RuntimeError("nytprofhtml not found")
    subprocess.check_call(["nytprofhtml", "-f", in_path, "-o", dest])
    return dest


def to_speedscope(in_path: str, out_path: str | None = None) -> str:
    attrs, files, defs, calls, lines = _parse(in_path)

    frames: list[dict] = []
    frame_map: dict[int, int] = {}
    events: list[dict] = []
    current = 0

    if calls:
        for fid, line, sid, inc, _exc in calls:
            info = defs.get(sid)
            pfid = info["fid"] if info else fid
            name = info["name"] if info else f"sub_{sid}"
            frame_name = f"{Path(files.get(pfid, {}).get('path', '')).name}:{name}"
            if sid not in frame_map:
                frame_map[sid] = len(frames)
                frames.append({"name": frame_name})
            idx = frame_map[sid]
            dur_us = inc // 10
            events.append({"type": "O", "at": current, "frame": idx})
            current += dur_us
            events.append({"type": "C", "at": current})
    else:
        for fid, line, _c, inc, _exc in lines:
            frame_name = f"{Path(files.get(fid, {}).get('path', '')).name}:{line}"
            key = (fid, line)
            if key not in frame_map:
                frame_map[key] = len(frames)
                frames.append({"name": frame_name})
            idx = frame_map[key]
            dur_us = inc // 10
            events.append({"type": "O", "at": current, "frame": idx})
            current += dur_us
            events.append({"type": "C", "at": current})

    result = {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "name": Path(in_path).name,
        "activeProfileIndex": 0,
        "shared": {"frames": frames},
        "profiles": [
            {
                "type": "evented",
                "name": "main",
                "unit": "microseconds",
                "startValue": 0,
                "endValue": current,
                "events": events,
            }
        ],
    }

    dest = out_path or str(Path(in_path).with_suffix(".speedscope.json"))
    Path(dest).write_text(json.dumps(result, indent=2))
    return dest
