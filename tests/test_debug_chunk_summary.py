import os, subprocess, sys
from pathlib import Path
from pynytprof._pywrite import _perl_nv_size


def test_debug_chunk_summary(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYNTP_FORCE_PY': '1',
        'PYNYTPROF_DEBUG': '1',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    proc = subprocess.run(
        [sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'],
        env=env, stderr=subprocess.PIPE, text=True
    )
    expected = f"DEBUG: wrote raw P record ({5 + 8 + _perl_nv_size()} B)"
    assert expected in proc.stderr
