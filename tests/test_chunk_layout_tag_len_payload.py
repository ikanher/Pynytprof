import struct
from pynytprof.reader import header_scan
from tests.utils import run_tracer


import pytest


@pytest.mark.xfail(reason="legacy outer chunk layout")
def test_chunk_layout(tmp_path):
    data = run_tracer(tmp_path).read_bytes()
    off = header_scan(data)[2]
    tags = []
    for _ in range(5):
        tag = data[off:off+1]; tags.append(tag)
        assert tag in (b'S', b'F', b'D', b'C', b'E')
        off += 1
        (length,) = struct.unpack_from("<I", data, off)
        off += 4
        off += length
    assert tags == [b'S', b'F', b'D', b'C', b'E']
