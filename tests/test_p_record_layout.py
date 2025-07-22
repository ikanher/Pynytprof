import os
import struct
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_p_record_layout(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    assert data[idx+1:idx+5] == struct.pack("<I", os.getpid())
    payload = data[idx+1:idx+17]
    assert len(payload) == 16
