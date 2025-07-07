import struct
import zlib
from pathlib import Path

import pytest
from pynytprof.writer import Writer


def test_text_header(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)):
        pass
    first = open(out, "rb").read().split(b"\n")[0]
    assert first == b"file=" + str(out).encode()


@pytest.mark.parametrize(
    "tag,data",
    [
        (b"F", b"x" * 100),
        (b"D", b"y" * 120),
        (b"C", b"z" * 80),
        (b"S", b"w" * 160),
    ],
)
def test_chunk_compression(tmp_path, tag, data):
    out = tmp_path / "out.nyt"
    with Writer(str(out)) as w:
        w._write_chunk(tag, data)
    buf = out.read_bytes()
    hdr_end = buf.index(b"\n\n") + 2
    on_disk = buf[hdr_end:]
    assert on_disk[0:1] == tag
    payload_len = struct.unpack("<I", on_disk[1:5])[0]
    payload = on_disk[5 : 5 + payload_len]
    assert len(payload) < len(data)


def test_file_chunk_uses_string_indexes(tmp_path):
    out = tmp_path / "out.nyt"
    foo = tmp_path / "foo.py"
    foo.write_text("x")
    with Writer(str(out)) as w:
        w._write_file_chunk([(str(foo), True)])
    buf = out.read_bytes()
    hdr_end = buf.index(b"\n\n") + 2
    after = buf[hdr_end:]
    assert after[0:1] == b"T"
    t_len = struct.unpack_from("<I", after, 1)[0]
    offset = 5 + t_len
    assert after[offset : offset + 1] == b"F"
    f_len = struct.unpack_from("<I", after, offset + 1)[0]
    payload = after[offset + 5 : offset + 5 + f_len]
    payload = zlib.decompress(payload)
    assert len(payload) == 20
    fid, pidx, didx, size, flags = struct.unpack("<IIIII", payload)
    assert pidx == 0
    assert didx == 1
    header_lines = buf[: hdr_end - 2].split(b"\n")
    assert b"stringtable=present" in header_lines
    assert b"stringcount=2" in header_lines


def test_close_writes_E_chunk(tmp_path):
    out = tmp_path / "out.nyt"
    foo = tmp_path / "foo.py"
    foo.write_text("y")
    with Writer(str(out)) as w:
        w._write_file_chunk([(str(foo), True)])
    buf = out.read_bytes()
    hdr_end = buf.index(b"\n\n") + 2
    after = buf[hdr_end:]
    off = 0
    last_tag = None
    while off < len(after):
        last_tag = after[off : off + 1]
        length = struct.unpack_from("<I", after, off + 1)[0]
        off += 5 + length
    assert last_tag == b"E"
    header_lines = buf[: hdr_end - 2].split(b"\n")
    assert b"has_end=1" in header_lines
    assert b"filecount=1" in header_lines
