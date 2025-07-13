from __future__ import annotations

import struct

__all__ = ["verify"]

MAGIC = b"NYTPROF\0"
MAJOR = 5
MINOR = 0
ASCII_PREFIX = b"NYTProf 5 0\n"


def verify(path: str, quiet: bool = False) -> bool:
    """Stream-verify a NYTProf file."""
    try:
        with open(path, "rb") as f:
            first = f.read(len(ASCII_PREFIX))
            if first == ASCII_PREFIX:
                while True:
                    pos = f.tell()
                    line = f.readline()
                    if not line:
                        raise ValueError("truncated header")
                    if line == b"\n":
                        break
                    if not line.startswith((b"#", b":", b"!")):
                        f.seek(pos)
                        break
                major = MAJOR
                minor = MINOR
            else:
                f.seek(0)
                if f.read(8) != MAGIC:
                    raise ValueError("bad header")
                maj_b = f.read(4)
                min_b = f.read(4)
                if len(maj_b) != 4 or len(min_b) != 4:
                    raise ValueError("truncated version")
                major = struct.unpack("<I", maj_b)[0]
                minor = struct.unpack("<I", min_b)[0]
                if (major, minor) != (MAJOR, MINOR):
                    raise ValueError("bad version")
                while True:
                    b = f.read(1)
                    if not b:
                        raise ValueError("truncated attrs")
                    if b in b"ACDFSET":
                        f.seek(-1, 1)
                        break
                    while b != b"\0":
                        b = f.read(1)
                        if not b:
                            raise ValueError("truncated attrs")
            last = None
            count = 0
            first = True
            while True:
                tag = f.read(1)
                if not tag:
                    raise ValueError("truncated tag")
                if first and tag == b"P":
                    payload = f.read(16)
                    if len(payload) != 16:
                        raise ValueError("truncated payload")
                    length = 16
                    first = False
                else:
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
