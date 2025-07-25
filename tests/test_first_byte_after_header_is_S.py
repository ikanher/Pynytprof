import struct
from pynytprof.reader import header_scan
from tests.utils import run_tracer


def test_first_byte_after_header_is_S(tmp_path):
    out = run_tracer(tmp_path)
    data = out.read_bytes()
    off = header_scan(data)[2]
    assert data[off:off+1] == b'S'
