import struct
import zlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pynytprof.writer import Writer, _MAGIC
import mmap


def test_text_header(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)):
        pass
    hdr = out.read_bytes()[:16]
    assert hdr.startswith(_MAGIC)


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
    hdr_end = 0
    for _ in range(10):
        hdr_end = buf.index(b"\n", hdr_end) + 1
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
    hdr_end = 0
    for _ in range(10):
        hdr_end = buf.index(b"\n", hdr_end) + 1
    after = buf[hdr_end:]
    assert after[0:1] == b"T"
    t_len = struct.unpack_from("<I", after, 1)[0]
    offset = 5 + t_len
    tag = after[offset : offset + 1]
    f_len = struct.unpack_from("<I", after, offset + 1)[0]
    payload = after[offset + 5 : offset + 5 + f_len]
    payload = zlib.decompress(payload)
    assert len(payload) == 20
    fid, pidx, didx, size, flags = struct.unpack("<IIIII", payload)
    assert pidx == 0
    assert didx == 1
    # header should remain unchanged after writing chunks


def test_close_writes_E_chunk(tmp_path):
    out = tmp_path / "out.nyt"
    foo = tmp_path / "foo.py"
    foo.write_text("y")
    with Writer(str(out)) as w:
        w._write_file_chunk([(str(foo), True)])
    buf = out.read_bytes()
    hdr_end = 0
    for _ in range(10):
        hdr_end = buf.index(b"\n", hdr_end) + 1
    after = buf[hdr_end:]
    off = 0
    last_tag = None
    while off < len(after):
        last_tag = after[off : off + 1]
        length = struct.unpack_from("<I", after, off + 1)[0]
        off += 5 + length
    assert last_tag == b"E"
    # header stays the same regardless of close operations


def test_statement_chunk(tmp_path):
    out = tmp_path / "out.nyt"
    foo = tmp_path / "foo.py"
    bar = tmp_path / "bar.py"
    foo.write_text("print('foo')")
    bar.write_text("print('bar')")
    with Writer(str(out)) as w:
        w._write_file_chunk([(str(foo), True), (str(bar), False)])
        for ln in range(1, 6):
            w.record_statement(0, ln, None)
            w.record_statement(1, ln, None)

    with out.open("rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        hdr_end = 0
        for _ in range(10):
            hdr_end = mm.find(b"\n", hdr_end) + 1
        off = hdr_end
        found = False
        while off < mm.size():
            tag = mm[off : off + 1]
            length = struct.unpack_from("<I", mm, off + 1)[0]
            off += 5
            payload = mm[off : off + length]
            off += length
            if tag == b"D":
                data = zlib.decompress(payload)
                assert struct.unpack_from("<I", data, 0)[0] == 0
                assert len(data) % 20 == 0
                found = True
                break
        mm.close()
    assert found, "D chunk not found"
