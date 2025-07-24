import os
import subprocess
import sys
import struct
from pathlib import Path


def test_banner_has_nv_size(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    data = out.read_bytes()
    header = data.split(b"\nP", 1)[0] + b"\n"
    nv = struct.calcsize("d")
    assert f":nv_size={nv}\n".encode() in header, "missing :nv_size banner line"
