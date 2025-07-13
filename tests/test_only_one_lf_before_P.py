import os
import subprocess
import sys
from pathlib import Path


def test_only_one_lf_before_P(tmp_path):
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
    i = data.index(b'\nP')
    assert data[i:i+2] == b'\nP'
    assert i == data.index(b'\nP')  # ensure no earlier instance
