import os
import struct
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_p_record_tlv_bytes(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    i = data.index(b"\nP") + 1
    assert data[i:i+1] == b"P"
    payload = data[i+1:i+17]
    pid, ppid, ts = struct.unpack("<IId", payload)
    assert pid == os.getpid()
    assert ppid == os.getppid()
