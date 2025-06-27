import struct
from pathlib import Path

__all__ = ["read"]


EXPECT = b"NYTPROF\x00\x05\x00\x00\x00\x00\x00\x00\x00"
H_CHUNK = b"H" + (8).to_bytes(4, "little") + (5).to_bytes(4, "little") + (0).to_bytes(4, "little")


def read(path: str) -> dict:
    data = Path(path).read_bytes()
    if data[:16] != EXPECT:
        raise ValueError("bad header")
    if data[16:29] != H_CHUNK:
        raise ValueError("bad H chunk")
    offset = 29
    result = {
        "header": (5, 0),
        "attrs": {},
        "files": {},
        "records": [],
    }
    while offset < len(data):
        tok = data[offset:offset + 1]
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
        payload = data[offset:offset + length]
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
        elif tok == "E":
            if length != 0:
                raise ValueError("bad E length")
            break
        else:
            raise ValueError(f"unknown token {tok}")
    return result
