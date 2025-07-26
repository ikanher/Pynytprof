from pathlib import Path
import io
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.protocol import read_u32


def test_p_chunk_is_17_bytes_writer():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[0:1] == b'P'
    _, off = read_u32(data, 1)
    _, off = read_u32(data, off)
    assert len(data) == off + 8

