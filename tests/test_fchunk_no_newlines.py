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
    p = subprocess.Popen([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        '-e', 'pass',
    ], env=env)
    p.wait()
    data = out.read_bytes()
    idx = data.index(b'\nP') + 1
    assert data[idx:idx+1] == b'P'
    pid_bytes = p.pid.to_bytes(4, 'little')
    assert data[idx+5:idx+9] == pid_bytes
    payload = data[idx+9:idx+21]
    assert b'\n' not in payload
