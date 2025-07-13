import os
import subprocess
import sys
import struct
import time
from pathlib import Path
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
    payload = data[idx + 1 : idx + 17]
    pid, ppid, ts = struct.unpack("<IId", payload)
    assert pid == p.pid
    assert ppid == os.getpid()
    assert abs(ts - time.time()) < 1.0
