import pytest
pytestmark = pytest.mark.legacy_psfdce
import os
import subprocess
import sys
from pathlib import Path
from tests.conftest import parse_chunks


def test_single_p_record(tmp_path):
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
    chunks = parse_chunks(data)
    p_chunk = chunks['P']
    pid = int.from_bytes(p_chunk['payload'][:4], 'little')
    assert pid == p.pid
    assert 'S' in chunks
