from tests.conftest import get_chunk_start
import os
import subprocess
import sys
from pathlib import Path


def test_p_chunk_pid_matches_process(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    p.wait()
    data = out.read_bytes()
    idx = get_chunk_start(data)
    assert data[idx : idx + 1] == b"P"
    length = int.from_bytes(data[idx + 1 : idx + 5], "little")
    assert length == 16
    pid_le = int.from_bytes(data[idx + 5 : idx + 9], "little")
    assert pid_le == p.pid, f"P-chunk PID {pid_le} != subprocess pid {p.pid}"
