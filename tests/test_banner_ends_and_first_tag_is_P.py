import os
import subprocess
import sys
from pathlib import Path


def test_banner_ends_and_first_tag_is_P(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        '-e', 'pass',
    ], env=env)
    data = out.read_bytes()
    idx = data.index(b'\n\nP')
    assert data[idx:idx+3] == b"\n\nP"
