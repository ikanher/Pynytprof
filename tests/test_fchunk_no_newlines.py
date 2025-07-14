import os
import subprocess
import sys
from pathlib import Path
from tests.conftest import parse_chunks


def test_pchunk_no_newlines(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    p = subprocess.Popen([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        '-e', 'pass',
    ], env=env)
    p.wait()
    data = out.read_bytes()
    chunks = parse_chunks(data)
    assert 'P' in chunks
    p_chunk = chunks['P']
    assert b'\n' not in p_chunk['payload'][:1]
    pid = int.from_bytes(p_chunk['payload'][:4], 'little')
    assert pid == p.pid
