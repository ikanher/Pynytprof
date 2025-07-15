import os, subprocess, sys, struct
from pathlib import Path


def test_only_one_p_record_and_no_length(tmp_path):
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
    positions = [i + 1 for i in range(len(data)) if data[i:i+2] == b"\nP"]
    assert len(positions) == 1, f"expected 1 P chunk, found {len(positions)}"
    idx = positions[0]
    pid = int.from_bytes(data[idx+1:idx+5], "little")
    assert pid == p.pid, "P chunk still has length word!"

