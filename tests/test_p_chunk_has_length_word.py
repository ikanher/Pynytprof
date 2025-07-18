import os, struct, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start


def test_p_chunk_contains_length(tmp_path):
    env = {**os.environ,
           "PYNYTPROF_WRITER": "py",
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    out = tmp_path / "nytprof.out"
    p = subprocess.Popen([sys.executable, "-m", "pynytprof.tracer",
                          "-o", str(out), "-e", "pass"], env=env)
    p.wait()
    data = out.read_bytes()
    idx = get_chunk_start(data)
    length = struct.unpack_from('<I', data, idx+1)[0]
    assert length == 16, f"P-chunk length {length} != 16"
    pid   = struct.unpack_from('<I', data, idx+5)[0]
    assert pid == p.pid, "PID not at offset 5"
