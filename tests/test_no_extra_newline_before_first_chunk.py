import os
import subprocess
import sys
from pathlib import Path


def test_no_extra_newline_before_first_chunk(tmp_path):
    out = tmp_path/'nytprof.out'
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
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
    idx = data.index(b'\nP')
    assert data[idx+1:idx+2] == b'P', f"Found {data[idx+1:idx+2]!r} before first chunk"

