from __future__ import annotations

import struct

from ._proto import (
    encode_u32,
    encode_i32,
    le32,
    ledouble,
    write_string,
)
from .tokens import (
    NYTP_TAG_NEW_FID,
    NYTP_TAG_SRC_LINE,
    NYTP_TAG_STRING,
    NYTP_TAG_STRING_UTF8,
    NYTP_TAG_TIME_LINE,
)


def output_str_py(val: bytes | str, utf8: bool = False) -> bytes:
    if isinstance(val, str):
        data = val.encode("utf-8")
    else:
        data = val
    return write_string(data, utf8=utf8)


class TokenWriter:
    def write_p_record(self, pid: int, ppid: int, t: float) -> bytes:
        return b"P" + le32(pid) + le32(ppid) + ledouble(t)

    def write_new_fid(
        self,
        fid: int,
        eval_fid: int,
        eval_line: int,
        flags: int,
        size: int,
        mtime: int,
        path: str | bytes,
    ) -> bytes:
        if isinstance(path, bytes):
            p = path
            utf8 = False
        else:
            p = path.encode("utf-8")
            utf8 = True
        out = bytearray()
        out.append(NYTP_TAG_NEW_FID)
        out += encode_u32(fid)
        out += encode_u32(eval_fid)
        out += encode_u32(eval_line)
        out += encode_u32(flags)
        out += encode_u32(size)
        out += encode_u32(mtime)
        out += output_str_py(p, utf8=utf8)
        return bytes(out)

    def write_src_line(
        self,
        fid: int,
        line_no: int,
        text: bytes | str,
        is_utf8: bool = False,
    ) -> bytes:
        if isinstance(text, str):
            data = text.encode("utf-8")
            is_utf8 = True
        else:
            data = text
        out = bytearray()
        out.append(NYTP_TAG_SRC_LINE)
        out += encode_u32(fid)
        out += encode_u32(line_no)
        out += output_str_py(data, utf8=is_utf8)
        return bytes(out)

    def write_time_line(
        self, fid: int, line_no: int, elapsed: int, overflow: int
    ) -> bytes:
        out = bytearray()
        out.append(NYTP_TAG_TIME_LINE)
        out += encode_i32(elapsed)
        out += encode_u32(fid)
        out += encode_u32(line_no)
        return bytes(out)
