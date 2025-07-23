import os
import subprocess
import sys
from pathlib import Path


def test_one_lf_before_p_in_real_run(tmp_path):
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    script = Path(__file__).resolve().parents[1] / 'tests' / 'example_script.py'
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        str(script),
    ], cwd=tmp_path, env=env)
    out = next(Path(tmp_path).glob('nytprof.out.*'))
    data = out.read_bytes()
    p_off = data.index(b'\nP') + 1
    assert data[p_off-1] == 0x0A and data[p_off-2] != 0x0A, "exactly one LF before 'P'"
