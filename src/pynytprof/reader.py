from pathlib import Path
import struct

__all__ = ["read"]

_MAGIC = b"NYTPROF\0"
_MAJOR = 5
_MINOR = 0
_ASCII_PREFIX = b"NYTProf 5 0\n"
_CHUNK_START = b"PACDFSET"


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
    while offset < len(data):
        tok = data[offset : offset + 1]
        if not tok:
            raise ValueError("unexpected EOF")
        tok = tok.decode()
        offset += 1
        if first and tok == "P":
            if offset + 16 > len(data):
                raise ValueError("truncated P chunk")
            length = 16
            payload = data[offset : offset + length]
            offset += length
            first = False
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
            if len(payload) != 16:
                raise ValueError("bad P length")
            start, pid, ppid = struct.unpack_from("<QII", payload, 0)
            result["attrs"].update({"start_time": start, "pid": pid, "ppid": ppid})
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
