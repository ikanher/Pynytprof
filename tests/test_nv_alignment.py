import pytest
pytestmark = pytest.mark.legacy_psfdce
import io
import re
import struct
from pynytprof._pywrite import Writer


def test_nv_alignment():
    buf = io.BytesIO()
    w = Writer(fp=buf, script_path='x')
    w._write_header()
    pos_after_p = buf.tell()

    data = buf.getvalue()
    header = data.split(b"\nP", 1)[0] + b"\n"
    m = re.search(rb":nv_size=(\d+)", header)
    assert m, "nv_size not found in header"
    nv_size = int(m.group(1))

    expected = len(header) + 1 + 4 + 4 + nv_size
    assert pos_after_p == expected

    w._write_chunk(b"S", b"")
    assert buf.getvalue()[pos_after_p:pos_after_p + 1] == b"S"
