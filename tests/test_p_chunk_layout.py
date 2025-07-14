import os
import struct
import subprocess
import sys
from pathlib import Path


def test_p_chunk_has_no_length_word(tmp_path):
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
    pid = int.from_bytes(data[idx + 1 : idx + 5], "little")
    assert pid == p.pid, (
        "Found length word instead of PID — P chunk layout is wrong"
    )
    assert data[idx + 17 : idx + 18] == b"S", "S tag not at expected offset"
