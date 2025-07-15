import os
import subprocess
import sys
from pathlib import Path


def test_exact_two_newlines_before_P(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    p.wait()
    data = out.read_bytes()
    idx = data.index(b"\n\nP") + 2
    count = 0
    i = idx - 1
    while i >= 0 and data[i] == 0x0A:
        count += 1
        i -= 1
    assert count == 2, f"Expected 2 blank lines before P, found {count}"
