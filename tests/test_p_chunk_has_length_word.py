import os, struct, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start


def test_p_chunk_payload_length(tmp_path):
    env = {**os.environ,
           "PYNYTPROF_WRITER": "py",
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    out = tmp_path / "nytprof.out"
    p = subprocess.Popen([sys.executable, "-m", "pynytprof.tracer",
                          "-o", str(out), "-e", "pass"], env=env)
    p.wait()
    data = out.read_bytes()
    idx = get_chunk_start(data)
    payload = data[idx + 5 : idx + 21]
    assert len(payload) == 16
    pid = struct.unpack_from('<I', payload)[0]
    assert pid == p.pid
