from pathlib import Path
import sys
import os
import struct
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_single_p_record(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    pid_bytes = struct.pack("<I", os.getpid())
    length16 = (16).to_bytes(4, "little")
    assert data.count(b"P" + length16 + pid_bytes) == 1
