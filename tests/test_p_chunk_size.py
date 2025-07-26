import io
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.protocol import read_u32
from pynytprof._pywrite import Writer

def test_p_record_is_17_bytes():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[:1] == b'P'
    pid, off = read_u32(data, 1)
    _, off = read_u32(data, off)
    assert len(data) == off + 8

