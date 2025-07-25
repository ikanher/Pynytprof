import struct
from pynytprof.reader import header_scan
from pynytprof.protocol import read_u32
from pynytprof.tags import KNOWN_TAGS
from tests.utils import run_tracer


def test_first_values_in_S_are_varints(tmp_path):
    out = run_tracer(tmp_path)
    data = out.read_bytes()
    off = header_scan(data)[2]
    assert data[off:off+1] == b'S'
    off += 1
    (slen,) = struct.unpack_from('<I', data, off)
    off += 4
    payload = data[off:off+slen]

    # should not be little-endian fixed width encoding
    assert payload[:4] != b"\x01\x00\x00\x00"

    tag = payload[0]
    assert tag in KNOWN_TAGS
    val, nxt = read_u32(payload, 1)
    assert nxt <= 5
