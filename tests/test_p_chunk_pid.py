from tests.conftest import get_chunk_start
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.protocol import read_u32


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
    pid, _ = read_u32(data, idx + 1)
    assert pid == p.pid, f"P-chunk PID {pid} != subprocess pid {p.pid}"
