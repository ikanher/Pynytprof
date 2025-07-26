"""Low-level NYTProf binary stream helpers."""

import struct

from .encoding import encode_u32, encode_i32

__all__ = [
    "TAG_NEW_FID",
    "TAG_TIME_BLOCK",
    "TAG_TIME_LINE",
    "TAG_SUB_ENTRY",
    "TAG_SUB_RETURN",
    "TAG_SUB_INFO",
    "TAG_SUB_CALLERS",
    "TAG_SRC_LINE",
    "TAG_DISCOUNT",
    "TAG_PID_END",
    "TAG_STRING",
    "TAG_STRING_UTF8",
    "write_byte",
    "write_le32",
    "write_ledouble",
    "write_u32_var",
    "write_i32_var",
    "write_nv",
    "write_process_start",
    "write_process_end",
    "write_new_fid",
    "write_time_line",
    "write_src_line",
]

# Token values mirror those defined in NYTProf's FileHandle.h
TAG_NEW_FID = 8
TAG_TIME_BLOCK = 5
TAG_TIME_LINE = 6
TAG_SUB_ENTRY = 17
TAG_SUB_RETURN = 18
TAG_SUB_INFO = 10
TAG_SUB_CALLERS = 11
TAG_SRC_LINE = 9
TAG_DISCOUNT = 7
TAG_PID_END = 13
TAG_STRING = 14
TAG_STRING_UTF8 = 15
TAG_START_DEFLATE = 16


def write_byte(b: int) -> bytes:
    return bytes([b & 0xFF])


def write_le32(n: int) -> bytes:
    return struct.pack("<I", n)


def write_ledouble(v: float) -> bytes:
    return struct.pack("<d", v)


def write_u32_var(n: int) -> bytes:
    return encode_u32(n)


def write_i32_var(n: int) -> bytes:
    return encode_i32(n)


def write_nv(v: float) -> bytes:
    return struct.pack("<d", v)


def write_process_start(pid: int, ppid: int, ts: float) -> bytes:
    return b"P" + write_le32(pid) + write_le32(ppid) + write_ledouble(ts)


def write_process_end(pid: int, ts: float) -> bytes:
    out = bytearray()
    out += write_byte(TAG_PID_END)
    out += write_u32_var(pid)
    out += write_nv(ts)
    return bytes(out)


def write_new_fid(
    fid: int,
    eval_fid: int,
    eval_line: int,
    flags: int,
    size: int,
    mtime: int,
    name: str | bytes,
    is_utf8: bool = False,
) -> bytes:
    if isinstance(name, str):
        data = name.encode("utf-8")
        is_utf8 = True
    else:
        data = name
    out = bytearray()
    out += write_byte(TAG_NEW_FID)
    out += write_u32_var(fid)
    out += write_u32_var(eval_fid)
    out += write_u32_var(eval_line)
    out += write_u32_var(flags)
    out += write_u32_var(size)
    out += write_u32_var(mtime)
    length = len(data)
    out += write_byte(TAG_STRING_UTF8 if is_utf8 else TAG_STRING)
    out += write_u32_var(length)
    out += data
    return bytes(out)


def write_time_line(elapsed: int, overflow: int, fid: int, line: int) -> bytes:
    out = bytearray()
    out += write_byte(TAG_TIME_LINE)
    out += write_i32_var(elapsed)
    out += write_u32_var(fid)
    out += write_u32_var(line)
    return bytes(out)


def write_src_line(fid: int, line: int, text: str | bytes, is_utf8: bool = False) -> bytes:
    if isinstance(text, str):
        data = text.encode("utf-8")
        is_utf8 = True
    else:
        data = text
    out = bytearray()
    out += write_byte(TAG_SRC_LINE)
    out += write_u32_var(fid)
    out += write_u32_var(line)
    length = len(data)
    out += write_byte(TAG_STRING_UTF8 if is_utf8 else TAG_STRING)
    out += write_u32_var(length)
    out += data
    return bytes(out)
