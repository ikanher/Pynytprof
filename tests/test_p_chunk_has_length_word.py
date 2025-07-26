import os
import subprocess
import sys
from pathlib import Path
from tests.conftest import get_chunk_start
from pynytprof.encoding import encode_u32, decode_u32


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
    off = idx + 1
    pid, off = decode_u32(data, off)
    ppid, off = decode_u32(data, off)
    length = off + 8 - (idx + 1)
    expected = len(encode_u32(pid)) + len(encode_u32(ppid)) + 8
    assert length == expected
    assert pid == p.pid
