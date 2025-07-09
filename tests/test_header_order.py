from pathlib import Path
import subprocess, os, sys

def test_first_token_is_F(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call([
        sys.executable,
        '-m','pynytprof.tracer',
        '-o', str(out),
        'tests/example_script.py'
    ], env=env)
    data = out.read_bytes()
    cutoff = data.index(b'\n\n') + 2
    assert data[cutoff] == 0x46  # 'F'
    assert data[cutoff - 1] == 0x0A  # banner ends with a blank line
