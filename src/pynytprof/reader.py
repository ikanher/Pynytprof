from pathlib import Path
import struct

from .protocol import read_u32

__all__ = ["read", "header_scan"]

_MAGIC = b"NYTPROF\0"
_MAJOR = 5
_MINOR = 0
_ASCII_PREFIX = b"NYTProf 5 0\n"
_CHUNK_START = b"PACDFSET"


def header_scan(data: bytes) -> tuple[int, int, int]:
    """Scan an ASCII NYTProf header returning offsets.

    Parameters
    ----------
    data:
        Full bytes of the profile file.

    Returns
    -------
    (header_len, p_pos, first_token_off)
    """

    if not data.startswith(_ASCII_PREFIX):
        raise ValueError("missing ASCII header")

    # expect first line exactly "NYTProf <major> <minor>\n"
    first_nl = data.find(b"\n")
    if first_nl == -1:
        raise ValueError("truncated header")
    if data[: first_nl + 1] != _ASCII_PREFIX:
        raise ValueError("bad header line")

    off = first_nl + 1
    nv_size: int | None = None

    while True:
        if off >= len(data):
            raise ValueError("truncated header")

        nl = data.find(b"\n", off)
        if nl == -1:
            raise ValueError("truncated header")

        line = data[off:nl]
        after = data[nl + 1 : nl + 2]

        # ensure ASCII only
        if any(b >= 0x80 for b in line):
            raise ValueError("non-ascii header")

        if line:
            if line.startswith((b":", b"!")) and b"=" in line:
                key, val = line[1:].split(b"=", 1)
                if key == b"nv_size":
                    try:
                        nv_size = int(val.decode())
                    except Exception as exc:
                        raise ValueError("bad nv_size") from exc
            elif line.startswith(b"#"):
                pass
            else:
                raise ValueError("malformed header line")

        if after == b"P":
            header_len = nl + 1
            p_pos = nl + 1
            break

        off = nl + 1

    if nv_size is None or nv_size not in {8, 16}:
        raise ValueError("missing or unsupported nv_size")

    off = p_pos + 1
    _, off = read_u32(data, off)
    _, off = read_u32(data, off)
    first_token_off = off + nv_size
    return header_len, p_pos, first_token_off


def read(path: str) -> dict:
    data = Path(path).read_bytes()
    attrs = {}
    if data.startswith(_ASCII_PREFIX):
        offset = 0
        line_end = data.find(b"\n")
        if line_end == -1:
            raise ValueError("truncated header")
        offset = line_end + 1
        major = _MAJOR
        minor = _MINOR
        while True:
            if offset >= len(data):
                raise ValueError("truncated header")
            if data[offset : offset + 1] in _CHUNK_START:
                break
            pos = offset
            line_end = data.find(b"\n", offset)
            if line_end == -1:
                raise ValueError("truncated header")
            line = data[offset:line_end]
            offset = line_end + 1
            if line == b"":
                break
            if line.startswith((b"#", b":", b"!")):
                if line.startswith(b":") and b"=" in line:
                    k, v = line[1:].split(b"=", 1)
                    try:
                        attrs[k.decode()] = int(v)
                    except ValueError:
                        attrs[k.decode()] = v.decode()
                continue
            else:
                offset = pos
                break
    else:
        if data[:8] != _MAGIC:
            raise ValueError("bad header")
        if len(data) < 16:
            raise ValueError("truncated header")
        major, minor = struct.unpack_from("<II", data, 8)
        if (major, minor) != (_MAJOR, _MINOR):
            raise ValueError("bad version")
        offset = 16
        while offset < len(data):
            end = data.find(b"\0", offset)
            if end == -1:
                raise ValueError("bad attrs")
            item = data[offset:end]
            offset = end + 1
            if not item:
                break
            if b"=" not in item:
                break
            key, val = item.split(b"=", 1)
            try:
                attrs[key.decode()] = int(val)
            except ValueError:
                attrs[key.decode()] = val.decode()
            if offset < len(data) and data[offset : offset + 1] in _CHUNK_START:
                break
    result = {
        "header": (major, minor),
        "attrs": attrs,
        "files": {},
        "defs": [],
        "calls": [],
        "records": [],
    }
    first = True
    nv_size = attrs.get("nv_size", 8)
    while offset < len(data):
        tok = data[offset : offset + 1]
        if not tok:
            raise ValueError("unexpected EOF")
        tok = tok.decode()
        offset += 1
        if first and tok == "P":
            start = offset
            pid, offset = read_u32(data, offset)
            ppid, offset = read_u32(data, offset)
            if offset + nv_size > len(data):
                raise ValueError("truncated payload")
            payload = data[start : offset + nv_size]
            offset += nv_size
            length = len(payload)
            first = False
        else:
            if tok == "E":
                length = 0
                payload = b""
            else:
                if offset + 4 > len(data):
                    raise ValueError("truncated length")
                length = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                if offset + length > len(data):
                    raise ValueError("truncated payload")
                payload = data[offset : offset + length]
                offset += length

        if tok == "A":
            if not payload or payload[-1] != 0:
                raise ValueError("attrs not nul terminated")
            for item in payload[:-1].split(b"\0"):
                if b"=" not in item:
                    raise ValueError("bad attr")
                k, v = item.split(b"=", 1)
                result["attrs"][k.decode()] = int(v)
        elif tok == "P":
            p = 0
            pid, p = read_u32(payload, p)
            ppid, p = read_u32(payload, p)
            if p + nv_size != len(payload):
                raise ValueError("bad P length")
            ts = struct.unpack_from("<d", payload, p)[0]
            result["attrs"].update({"pid": pid, "ppid": ppid, "timestamp": ts})
        elif tok == "F":
            if length % 8 != 0:
                raise ValueError("bad F record")
            p = 0
            while p < length:
                fid, stridx = struct.unpack_from("<II", payload, p)
                result["files"][fid] = {"string_index": stridx}
                p += 8
            if p != length:
                raise ValueError("bad F length")
        elif tok == "S":
            p = 0
            rec_size = 28
            while p + rec_size <= length:
                fid, line, calls, inc, exc = struct.unpack_from("<IIIQQ", payload, p)
                result["records"].append((fid, line, calls, inc, exc))
                p += rec_size
            if p != length:
                raise ValueError("bad S length")
        elif tok == "D":
            p = 0
            if length and payload[0] <= 7:
                while p < length:
                    tok_b = payload[p]
                    p += 1
                    if tok_b == 0:
                        break
                    if tok_b != 1 or p + 16 > length:
                        raise ValueError("bad D record")
                    fid, line, dur = struct.unpack_from("<IIQ", payload, p)
                    p += 16
                    result.setdefault("data", []).append((fid, line, dur))
                if p != length:
                    raise ValueError("bad D length")
            else:
                try:
                    while p < length:
                        if p + 16 > length:
                            raise ValueError
                        sid, fid, sl, el = struct.unpack_from("<IIII", payload, p)
                        p += 16
                        end = payload.find(b"\0", p)
                        if end == -1 or end >= length:
                            raise ValueError
                        name = payload[p:end].decode()
                        p = end + 1
                        result["defs"].append((sid, fid, sl, el, name))
                    if p != length:
                        raise ValueError
                except Exception:
                    result["defs"].clear()
                    p = 0
                    while p < length:
                        if p + 8 > length:
                            raise ValueError("bad D record")
                        sid, flags = struct.unpack_from("<II", payload, p)
                        p += 8
                        end = payload.find(b"\0", p)
                        if end == -1 or end >= length:
                            raise ValueError("bad D name")
                        name = payload[p:end].decode()
                        p = end + 1
                        result["defs"].append((sid, flags, 0, 0, name))
                    if p != length:
                        raise ValueError("bad D length")
        elif tok == "C":
            p = 0
            rec_size = 28
            while p + rec_size <= length:
                fid, line, sid, inc, exc = struct.unpack_from("<IIIQQ", payload, p)
                result["calls"].append((fid, line, sid, inc, exc))
                p += rec_size
            if p != length:
                raise ValueError("bad C length")
        elif tok == "E":
            if length != 0:
                raise ValueError("bad E length")
            break
        else:
            raise ValueError(f"unknown token {tok}")
    return result
