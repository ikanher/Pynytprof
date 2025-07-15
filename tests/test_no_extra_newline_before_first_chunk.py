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
    idx = data.index(b'\n\nP')
    assert data[idx+2:idx+3] == b'P', f"Found {data[idx+2:idx+3]!r} before first chunk"

