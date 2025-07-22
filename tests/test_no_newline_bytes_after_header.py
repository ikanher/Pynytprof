from tests.conftest import get_chunk_start
import os, subprocess, sys
from pathlib import Path

def test_no_newline_bytes_after_header(tmp_path):
    out = tmp_path/'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call(
        [sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'],
        env=env
    )
    data = out.read_bytes()
    split = get_chunk_start(data)
    # Ensure binary section starts exactly at 'P'
    assert data[split:split + 1] == b'P'
    # And that there is a newline just before it (end of banner)
    assert data[split - 1:split] == b"\n"

