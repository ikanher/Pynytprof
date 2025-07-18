import os
import subprocess
import sys
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
    assert b":nv_size=8\n" in header, "missing :nv_size=8 banner line"
