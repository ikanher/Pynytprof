from pathlib import Path
import sys
import os
import struct
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_no_buffer_chunk_for_p(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    length16 = (16).to_bytes(4, "little")
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    assert data[idx+1:idx+5] == length16
    assert data.count(b"P" + length16) == 1
