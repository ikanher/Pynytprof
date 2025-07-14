import os
import subprocess
import sys
from pathlib import Path


def test_pchunk_no_newlines(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        '-e', 'pass',
    ], env=env)
    data = out.read_bytes()
    idx = data.index(b'\nP') + 1
    assert data[idx:idx+1] == b'P'
    assert data[idx+1:idx+5] == (16).to_bytes(4, 'little')
    payload = data[idx+5:idx+21]
    assert b'\n' not in payload
