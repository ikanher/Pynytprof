from tests.conftest import get_chunk_start
import os
import subprocess
import sys
import struct
import time
from pathlib import Path
import pytest
from pynytprof.encoding import decode_u32


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
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b"P"
    off = idx + 1
    pid, off = decode_u32(data, off)
    ppid, off = decode_u32(data, off)
    ts = struct.unpack("<d", data[off:off + 8])[0]
    assert pid == p.pid
    assert ppid == os.getpid()
    assert abs(ts - time.time()) < 1.0

