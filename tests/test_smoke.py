from pathlib import Path
import subprocess
import sys

def test_profile_creates_file(tmp_path):
    script = Path(__file__).with_name('example_script.py')
    out = tmp_path / 'nytprof.out'
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', str(script)], cwd=tmp_path)
    assert out.exists() and out.stat().st_size >= 8
