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
    assert data[i:i+5] == b"P\x10\x00\x00\x00"
    pid, ppid, ts = struct.unpack("<IId", data[i+5:i+21])
    assert pid == os.getpid()
    assert ppid == os.getppid()
