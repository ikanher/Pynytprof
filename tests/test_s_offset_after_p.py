import struct
import os
import subprocess
import sys
from pathlib import Path
from tests.conftest import parse_chunks


def test_s_offset_after_p(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    data = out.read_bytes()
    chunks = parse_chunks(data)
    assert 'P' in chunks and 'S' in chunks
    p_chunk = chunks['P']
    s_chunk = chunks['S']
    assert s_chunk['offset'] > p_chunk['offset'] + 5 + p_chunk['length']
