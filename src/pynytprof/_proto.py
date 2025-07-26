from __future__ import annotations

import struct

from .encoding import (
    encode_u32 as _encode_u32,
    encode_i32 as _encode_i32,
    le32,
    ledouble,
    output_str,
)
from .nytprof_tags import NYTP_TAG_STRING, NYTP_TAG_STRING_UTF8


def encode_u32(n: int) -> bytes:
    return _encode_u32(n)


def encode_i32(n: int) -> bytes:
    return _encode_i32(n)


def write_string(data: bytes, utf8: bool = False) -> bytes:
    return output_str(data, utf8=utf8)
