from __future__ import annotations

import struct

from .protocol import write_tag_u32, write_u32
from .tokens import (
    NYTP_TAG_NEW_FID,
    NYTP_TAG_SRC_LINE,
    NYTP_TAG_STRING,
    NYTP_TAG_STRING_UTF8,
)


def output_str_py(val: bytes | str, utf8: bool = False) -> bytes:
    if isinstance(val, str):
        data = val.encode("utf-8")
    else:
        data = val
    tag = NYTP_TAG_STRING_UTF8 if utf8 else NYTP_TAG_STRING
    out = bytearray()
    out += write_tag_u32(tag, len(data))
    out += data
    return bytes(out)


class TokenWriter:
    def write_p_record(self, pid: int, ppid: int, t: float) -> bytes:
        payload = struct.pack("<I", pid)
        payload += struct.pack("<I", ppid)
        payload += struct.pack("<d", t)
        return b"P" + payload

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
        out += write_tag_u32(NYTP_TAG_NEW_FID, fid)
        out += write_u32(eval_fid)
        out += write_u32(eval_line)
        out += write_u32(flags)
        out += write_u32(size)
        out += write_u32(mtime)
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
        out += write_tag_u32(NYTP_TAG_SRC_LINE, fid)
        out += write_u32(line_no)
        out += output_str_py(data, utf8=is_utf8)
        return bytes(out)
