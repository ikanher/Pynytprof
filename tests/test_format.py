from pathlib import Path
import subprocess
import sys
import time
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.reader import read, EXPECTED


import pytest


@pytest.mark.parametrize("extra_env", [{}, {"PYNTP_FORCE_PY": "1"}])
def test_format(tmp_path, extra_env):
    script = Path(__file__).with_name('example_script.py')
    out = tmp_path / 'nytprof.out'
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    env.update(extra_env)
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', str(script)], cwd=tmp_path, env=env)
    assert out.exists()
    assert out.open('rb').read(16) == EXPECTED
    start = time.perf_counter()
    data = read(str(out))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f'reader too slow: {elapsed_ms:.2f} ms'

    assert data['header'] == (5, 0)
    assert data['attrs'].get('ticks_per_sec') == 10_000_000
    assert data['records']
    lines = [r[1] for r in data['records']]
    assert all(l > 0 for l in lines)
    assert lines == sorted(lines)
