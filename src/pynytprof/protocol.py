"""Low-level NYTProf integer encoding helpers."""

from __future__ import annotations

NYTP_TAG_NO_TAG = 256  # sentinel meaning no tag byte should be written

__all__ = [
    "NYTP_TAG_NO_TAG",
    "write_tag_u32",
    "write_tag_i32",
    "write_u32",
    "write_i32",
    "read_u32",
    "read_i32",
    "is_valid_varint_prefix",
    "output_str",
]


def write_tag_u32(tag: int, val: int) -> bytes:
    """Return the NYTProf varint encoding of ``val`` optionally prefixed by ``tag``."""
    out = bytearray()
    if tag != NYTP_TAG_NO_TAG:
        out.append(tag & 0xFF)

    i = val & 0xFFFFFFFF
    if i < 0x80:
        out.append(i)
    elif i < 0x4000:
        out.append((i >> 8) | 0x80)
        out.append(i & 0xFF)
    elif i < 0x200000:
        out.append((i >> 16) | 0xC0)
        out.append((i >> 8) & 0xFF)
        out.append(i & 0xFF)
    elif i < 0x10000000:
        out.append((i >> 24) | 0xE0)
        out.append((i >> 16) & 0xFF)
        out.append((i >> 8) & 0xFF)
        out.append(i & 0xFF)
    else:
        out.append(0xFF)
        out.append((i >> 24) & 0xFF)
        out.append((i >> 16) & 0xFF)
        out.append((i >> 8) & 0xFF)
        out.append(i & 0xFF)

    return bytes(out)


def write_tag_i32(tag: int, val: int) -> bytes:
    u = val & 0xFFFFFFFF
    return write_tag_u32(tag, u)


def write_u32(val: int) -> bytes:
    return write_tag_u32(NYTP_TAG_NO_TAG, val)


def write_i32(val: int) -> bytes:
    return write_tag_i32(NYTP_TAG_NO_TAG, val)


def read_u32(buf: bytes, off: int) -> tuple[int, int]:
    d = buf[off]
    off += 1

    if d < 0x80:
        newint = d
    else:
        if d < 0xC0:
            newint = d & 0x7F
            length = 1
        elif d < 0xE0:
            newint = d & 0x1F
            length = 2
        elif d < 0xFF:
            newint = d & 0xF
            length = 3
        else:
            newint = 0
            length = 4
        for b in buf[off:off + length]:
            newint = (newint << 8) | b
        off += length

    return newint, off


def read_i32(buf: bytes, off: int) -> tuple[int, int]:
    u, off = read_u32(buf, off)
    if u & 0x80000000:
        u = -((~u + 1) & 0xFFFFFFFF)
    return u, off


def is_valid_varint_prefix(b: int) -> bool:
    return 0 <= b <= 0xFF


def output_str(data: bytes, utf8: bool = False) -> bytes:
    """Return the NYTProf varint+raw representation of ``data``.

    If ``utf8`` is ``True`` the length is negated before encoding, mirroring the
    XS convention that a negative length denotes utf8 data.  The caller is
    responsible for prefixing any tag byte.
    """

    length = len(data)
    if utf8:
        length = -length
    return write_i32(length) + data

