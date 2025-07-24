import os
import subprocess
import sys
import re
import struct
from pathlib import Path


def test_banner_includes_nv_size(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    header, _ = data.split(b"\nP", 1)
    nv = struct.calcsize("d")
    assert f":nv_size={nv}\n".encode() in header
    p_off = len(header) + 1
    assert data[p_off:p_off + 1] == b"P"
