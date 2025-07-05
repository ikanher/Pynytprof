from __future__ import annotations

import struct

__all__ = ["verify"]

MAGIC = b"NYTPROF\0"


def verify(path: str, quiet: bool = False) -> bool:
    """Stream-verify a NYTProf file."""
    try:
        with open(path, "rb") as f:
            if f.read(8) != MAGIC:
                raise ValueError("bad header")
            f.read(8)  # version
            last = None
            count = 0
            while True:
                tag = f.read(1)
                if not tag:
                    raise ValueError("truncated tag")
                length_b = f.read(4)
                if len(length_b) != 4:
                    raise ValueError("truncated length")
                length = struct.unpack("<I", length_b)[0]
                payload = f.read(length)
                if len(payload) != length:
                    raise ValueError("truncated payload")
                count += 1
                last = tag
                if tag == b"E":
                    break
            if last != b"E":
                raise ValueError("missing E record")
    except Exception as exc:
        if not quiet:
            print(f"{path} \u2717 {exc}")
        return False
    if not quiet:
        print(f"{path} \u2713 {count} chunks")
    return True
