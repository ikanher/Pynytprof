import struct
import os
import subprocess
import sys
from pathlib import Path


def test_s_offset_after_p(tmp_path):
    out = tmp_path / "nytprof.out"
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
    idx_p = data.index(b"\nP") + 1
    s_expected = idx_p + 1 + 4 + 4 + 4 + 8
    idx_s = data.index(b"S", s_expected - 1)
    assert idx_s == s_expected
