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
    split = data.index(b'\nP') + 1 + 1 + 4 + 16
    tail = data[split:]
    # Assert no 0x0A anywhere in the binary section
    pos = tail.find(b'\n')
    assert pos == -1, f"Found newline in payload at offset {split + pos}"
