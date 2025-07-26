import os
import struct
import time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.reader import header_scan


def test_p_record_layout(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)) as w:
        w.start_profile()
        w.end_profile()
    data = out.read_bytes()
    _, p_pos, first_token = header_scan(data)
    assert data[p_pos:p_pos+1] == b"P"
    pid = struct.unpack_from("<I", data, p_pos + 1)[0]
    ppid = struct.unpack_from("<I", data, p_pos + 5)[0]
    ts = struct.unpack_from("<d", data, p_pos + 9)[0]
    assert pid == os.getpid()
    assert ppid == os.getppid()
    assert abs(ts - time.time()) < 5
