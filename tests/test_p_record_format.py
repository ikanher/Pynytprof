from tests.conftest import get_chunk_start
import os
import subprocess
import sys
import struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.protocol import read_u32
from tests.utils import parse_nv_size_from_banner
import time
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
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b"P"
    nv_size = parse_nv_size_from_banner(data)
    payload = data[idx + 1 :]
    pid, off = read_u32(payload, 0)
    ppid, off = read_u32(payload, off)
    ts = struct.unpack("<d", payload[off:off + nv_size])[0]
    assert pid == p.pid
    assert ppid == os.getpid()
    assert abs(ts - time.time()) < 1.0

