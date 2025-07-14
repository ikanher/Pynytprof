from pathlib import Path
import subprocess
import sys
import os

def test_profile_creates_file(tmp_path):
    script = Path(__file__).with_name('example_script.py')
    out = tmp_path / f"nytprof.out.{os.getpid()}"
    env = dict(**os.environ)
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    subprocess.check_call([
        sys.executable,
        '-m',
        'pynytprof.tracer',
        '-o',
        str(out),
        str(script)
    ], cwd=tmp_path, env=env)
    assert out.exists() and out.stat().st_size >= 8
