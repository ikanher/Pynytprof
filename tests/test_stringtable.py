import struct

from pynytprof.writer import _StringTable


def test_stringtable_roundtrip():
    tbl = _StringTable()
    assert tbl.add("foo") == 0
    assert tbl.add("bar") == 1
    assert tbl.add("foo") == 0
    payload = tbl.serialize()
    count = struct.unpack_from("<I", payload)[0]
    assert count == 2
    offset = 4
    out = []
    for _ in range(count):
        length = struct.unpack_from("<I", payload, offset)[0]
        offset += 4
        s = payload[offset : offset + length].decode()
        offset += length
        out.append(s)
    assert out == ["foo", "bar"]
    assert offset == len(payload)
