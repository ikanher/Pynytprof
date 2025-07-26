import os, struct, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start
from tests.utils import parse_nv_size_from_banner
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.protocol import read_u32


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
    nv_size = parse_nv_size_from_banner(data)
    payload = data[idx + 1 : idx + 1 + 20]  # read a bit more than needed
    pid, off = read_u32(payload, 0)
    ppid, off = read_u32(payload, off)
    assert pid == p.pid
    assert ppid == os.getpid()
    assert len(payload[:off + nv_size]) == off + nv_size
