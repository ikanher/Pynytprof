import struct

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
