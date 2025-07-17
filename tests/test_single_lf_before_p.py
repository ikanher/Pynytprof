from tests.conftest import get_chunk_start
import os
import subprocess
import sys
from pathlib import Path
import pytest


def test_single_lf_before_p(tmp_path):
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
    idx = get_chunk_start(data)
    assert data[idx - 1] == 0x0A
    assert data[idx - 2] != 0x0A

