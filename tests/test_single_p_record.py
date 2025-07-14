import os
import subprocess
import sys
from pathlib import Path


def test_single_p_record(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
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
    idx = data.index(b"\nP") + 1
    pid = int.from_bytes(data[idx + 5:idx + 9], "little")
    assert pid == p.pid
    assert data[idx + 21:idx + 22] == b"S"
