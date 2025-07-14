import os, subprocess, sys
from pathlib import Path


def test_no_buffered_p(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_DEBUG': '1',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    logs = subprocess.check_output(
        [sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), '-e', 'pass'],
        env=env, stderr=subprocess.STDOUT
    ).decode()
    assert 'buffering chunk tag=P' not in logs
