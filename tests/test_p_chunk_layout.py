from tests.conftest import get_chunk_start
import os
import struct
import subprocess
import sys
from pathlib import Path


def test_p_chunk_no_length_word(tmp_path):
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
    p_off = data.index(b"\nP") + 1
    pid = struct.unpack_from('<I', data, p_off + 1)[0]
    assert pid == p.pid, f"pid mismatch (found {pid}, expected {p.pid})"
    next_tag = data[p_off + 17 : p_off + 18]
    assert next_tag in b'SFDCE', f"unexpected next tag {next_tag!r}"
