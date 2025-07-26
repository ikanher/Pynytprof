import struct
from pynytprof.reader import header_scan
from pynytprof.protocol import read_u32
from pynytprof.tags import KNOWN_TAGS
from tests.utils import run_tracer


def test_first_values_in_S_are_varints(tmp_path):
    out = run_tracer(tmp_path)
    data = out.read_bytes()
    off = header_scan(data)[2]
    tag = data[off]
    assert tag in KNOWN_TAGS or chr(tag).isprintable()
    val, nxt = read_u32(data, off + 1)
    assert nxt - off <= 5
