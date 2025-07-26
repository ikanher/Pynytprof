import struct
from .nytprof_tags import NYTP_TAG_STRING, NYTP_TAG_STRING_UTF8


def encode_u32(n: int) -> bytes:
    """NYTProf varint encoding for unsigned 32-bit values."""
    assert 0 <= n <= 0xFFFFFFFF
    if n < 0x80:
        return bytes([n])
    elif n < 0x4000:
        return bytes([(n >> 8) | 0x80, n & 0xFF])
    elif n < 0x200000:
        return bytes([(n >> 16) | 0xC0, (n >> 8) & 0xFF, n & 0xFF])
    elif n < 0x10000000:
        return bytes([
            (n >> 24) | 0xE0,
            (n >> 16) & 0xFF,
            (n >> 8) & 0xFF,
            n & 0xFF,
        ])
    else:
        return bytes([
            0xFF,
            (n >> 24) & 0xFF,
            (n >> 16) & 0xFF,
            (n >> 8) & 0xFF,
            n & 0xFF,
        ])


def encode_i32(n: int) -> bytes:
    """Two's-complement pass-through used by NYTProf."""
    return encode_u32(n & 0xFFFFFFFF)


def le32(n: int) -> bytes:
    return struct.pack('<I', n & 0xFFFFFFFF)


def ledouble(x: float) -> bytes:
    return struct.pack('<d', float(x))


def output_str(b: bytes, utf8: bool = False) -> bytes:
    tag = NYTP_TAG_STRING_UTF8 if utf8 else NYTP_TAG_STRING
    return bytes([tag]) + encode_u32(len(b)) + b
