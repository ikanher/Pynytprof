from pathlib import Path
import io
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.encoding import encode_u32
import os


def test_p_chunk_length_writer():
    buf = io.BytesIO()
    w = Writer(fp=buf)
    w._write_raw_P()
    data = buf.getvalue()
    assert data[0:1] == b'P'
    expected = 1 + len(encode_u32(os.getpid())) + len(encode_u32(os.getppid())) + 8
    assert len(data) == expected

