from __future__ import annotations

import struct

__all__ = ["verify"]

MAGIC = b"NYTPROF\x00\x05\x00\x00\x00\x00\x00\x00\x00"


def _read_chunks(path: str):
    with open(path, "rb") as f:
        header = f.read(16)
        if len(header) != 16 or header != MAGIC:
            raise ValueError("bad header")
        while True:
            tag = f.read(1)
            if not tag:
                break
            length_b = f.read(4)
            if len(length_b) < 4:
                raise ValueError("truncated length")
            length = struct.unpack("<I", length_b)[0]
            payload = f.read(length)
            if len(payload) < length:
                raise ValueError("truncated payload")
            yield tag, payload
            if tag == b"E":
                break


def verify(path: str, quiet: bool = False) -> bool:
    try:
        last = None
        count = 0
        for tag, payload in _read_chunks(path):
            count += 1
            last = tag
            if len(payload) < 0:
                raise ValueError("bad payload")
        if last != b"E":
            raise ValueError("missing E record")
    except Exception as exc:
        if not quiet:
            print(f"{path} \u2717 {exc}")
        return False
    if not quiet:
        print(f"{path} \u2713 {count} chunks")
    return True
