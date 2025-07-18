from pathlib import Path
import io
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_p_chunk_is_21_bytes_writer():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[0:1] == b'P'
    assert len(data) == 21

