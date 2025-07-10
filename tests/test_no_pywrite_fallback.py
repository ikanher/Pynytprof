import os, subprocess, sys


from pathlib import Path


def test_tracer_does_not_fallback_to__writer(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYNTP_FORCE_CWRITE': '1',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    result = subprocess.run([
        sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'
    ], env=env, stderr=subprocess.PIPE, text=True)
    assert 'falling back to pure-Python writer' not in result.stderr

