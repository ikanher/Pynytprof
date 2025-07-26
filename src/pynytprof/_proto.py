from __future__ import annotations

import struct

from .encoding import encode_u32 as _encode_u32, encode_i32 as _encode_i32
from .tokens import NYTP_TAG_STRING, NYTP_TAG_STRING_UTF8


def le32(n: int) -> bytes:
    """Return ``n`` as little-endian 32-bit unsigned."""
    return struct.pack('<I', n & 0xFFFFFFFF)


def ledouble(x: float) -> bytes:
    """Return ``x`` as an IEEE-754 little-endian double."""
    return struct.pack('<d', float(x))


def encode_u32(n: int) -> bytes:
    return _encode_u32(n)


def encode_i32(n: int) -> bytes:
    return _encode_i32(n)


def write_string(data: bytes, utf8: bool = False) -> bytes:
    tag = NYTP_TAG_STRING_UTF8 if utf8 else NYTP_TAG_STRING
    return bytes([tag]) + encode_u32(len(data)) + data
