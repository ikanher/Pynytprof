from tests.conftest import get_chunk_start
import os
import struct
import subprocess
import sys
from pathlib import Path


def test_p_chunk_has_length_word(tmp_path):
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
    idx = get_chunk_start(data)
    length = struct.unpack_from('<I', data, idx+1)[0]
    assert length == 16, f"P length {length} != 16"
    pid = struct.unpack_from('<I', data, idx + 5)[0]
    assert pid == p.pid, "PID not at offset 5"
    assert data[idx + 21 : idx + 22] == b"S", "S tag not at expected offset"
