from pathlib import Path
import subprocess
import sys
import time
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.reader import read, EXPECT


import pytest


@pytest.mark.parametrize("hide_cwrite", [False, True])
def test_format(tmp_path, hide_cwrite):
    script = Path(__file__).with_name('example_script.py')
    out = tmp_path / 'nytprof.out'
    env = dict(os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    if hide_cwrite:
        fake = tmp_path / 'fake'
        pkg = fake / 'pynytprof'
        pkg.mkdir(parents=True)
        (pkg / '_cwrite.py').write_text('raise ImportError\n')
        env['PYTHONPATH'] = str(fake) + os.pathsep + env['PYTHONPATH']
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', str(script)], cwd=tmp_path, env=env)
    assert out.exists()
    assert out.open('rb').read(16) == EXPECT
    header = out.open('rb').read(29)
    assert header[16:29] == b'H\x08\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00'
    expected = b'H\x08\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00'
    with out.open('rb') as f:
        f.seek(16)
        assert f.read(13) == expected
    start = time.perf_counter()
    data = read(str(out))
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 50, f'reader too slow: {elapsed_ms:.2f} ms'

    assert data['header'] == (5, 0)
    assert data['attrs'].get('ticks_per_sec') == 10_000_000
    assert data['records']
    line_numbers = [r[1] for r in data['records']]
    assert all(num > 0 for num in line_numbers)
    assert line_numbers == sorted(line_numbers)
