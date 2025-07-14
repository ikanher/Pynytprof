from pathlib import Path
import io
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer, _perl_nv_size


def test_p_chunk_includes_length_field():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P(123, 456)
    data = buf.getvalue()
    plen = 8 + _perl_nv_size()
    assert data[0:1] == b'P'
    assert data[1:5] == struct.pack('<I', plen)
    assert data[5:9] == struct.pack('<I', 123)
    assert data[9:13] == struct.pack('<I', 456)
    assert len(data) == 5 + plen
