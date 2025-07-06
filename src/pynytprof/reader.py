import struct
from pathlib import Path

__all__ = ["read"]


PREFIX = b"NYTPROF\0"
VERSION = 5


def read(path: str) -> dict:
    data = Path(path).read_bytes()
    if data[:8] != PREFIX:
        raise ValueError("bad header")
    if len(data) < 20:
        raise ValueError("truncated header")
    version = struct.unpack_from("<I", data, 8)[0]
    if version != VERSION:
        raise ValueError("bad version")
    header_len = struct.unpack_from("<Q", data, 12)[0]
    if len(data) < 20 + header_len:
        raise ValueError("truncated payload")
    h_chunk = data[20 : 20 + header_len]
    if h_chunk[:1] != b"H":
        raise ValueError("bad H tag")
    h_len = struct.unpack_from("<I", h_chunk, 1)[0]
    if h_len != len(h_chunk) - 5:
        raise ValueError("bad H length")
    attrs_blob = h_chunk[5:]
    if attrs_blob and attrs_blob[-1] != 0:
        raise ValueError("H not nul terminated")
    offset = 20 + header_len
    result = {
        "header": (version, 0),
        "attrs": {},
        "files": {},
        "defs": [],
        "calls": [],
        "records": [],
    }
    if attrs_blob:
        for item in attrs_blob[:-1].split(b"\0"):
            if b"=" not in item:
                raise ValueError("bad attr")
            k, v = item.split(b"=", 1)
            try:
                result["attrs"][k.decode()] = int(v)
            except ValueError:
                result["attrs"][k.decode()] = v.decode()
    result = {
        "header": (5, 0),
        "attrs": {},
        "files": {},
        "defs": [],
        "calls": [],
        "records": [],
    }
    while offset < len(data):
        tok = data[offset : offset + 1]
        if not tok:
            raise ValueError("unexpected EOF")
        tok = tok.decode()
        offset += 1
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
            attrs = payload[:-1].split(b"\0")
            for item in attrs:
                if b"=" not in item:
                    raise ValueError("bad attr")
                k, v = item.split(b"=", 1)
                result["attrs"][k.decode()] = int(v)
        elif tok == "F":
            p = 0
            while p < length:
                if p + 16 > length:
                    raise ValueError("bad F record")
                fid, flags, size, mtime = struct.unpack_from("<IIII", payload, p)
                p += 16
                end = payload.find(b"\0", p)
                if end == -1 or end >= length:
                    raise ValueError("bad F path")
                path_str = payload[p:end].decode()
                p = end + 1
                result["files"][fid] = {
                    "path": path_str,
                    "flags": flags,
                    "size": size,
                    "mtime": mtime,
                }
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
            while p < length:
                if p + 16 > length:
                    raise ValueError("bad D record")
                sid, fid, sl, el = struct.unpack_from("<IIII", payload, p)
                p += 16
                end = payload.find(b"\0", p)
                if end == -1 or end >= length:
                    raise ValueError("bad D name")
                name = payload[p:end].decode()
                p = end + 1
                result["defs"].append((sid, fid, sl, el, name))
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
