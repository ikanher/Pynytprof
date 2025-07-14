import os
import subprocess
import sys
import struct
import time
from pathlib import Path
from pynytprof._pywrite import _perl_nv_size
import pytest


def test_p_record_format(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    p.wait()
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    nv_size = _perl_nv_size()
    payload = data[idx + 5 : idx + 5 + 8 + nv_size]
    pid = int.from_bytes(payload[0:4], "little")
    ppid = int.from_bytes(payload[4:8], "little")
    if nv_size == 8:
        ts = struct.unpack_from("<d", payload, 8)[0]
        assert abs(ts - time.time()) < 1.0
    assert pid == p.pid
    assert ppid == os.getpid()

