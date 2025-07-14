from pathlib import Path
import io
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_p_chunk_includes_length_field():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    payload = b'ABCDEFGH'
    w._write_raw_P(payload)
    data = buf.getvalue()
    assert data[0:1] == b'P'
    assert data[1:5] == struct.pack('<I', len(payload))
    assert data[5:] == payload
