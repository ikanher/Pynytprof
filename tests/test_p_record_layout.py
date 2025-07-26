import os
import struct
import time
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer




def test_p_record_layout(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    pid, ppid, ts = struct.unpack_from("<IId", data, idx + 1)
    assert pid == os.getpid()
    assert ppid == os.getppid()
    assert abs(ts - time.time()) < 5
