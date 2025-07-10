import os
import subprocess
import sys
from pathlib import Path

def test_no_newlines_after_chunks(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        'tests/example_script.py',
    ], env=env)
    data = out.read_bytes()
    off = data.index(b'\n\n') + 2
    while off < len(data):
        length = int.from_bytes(data[off + 1:off + 5], 'little')
        end = off + 5 + length
        assert data[end:end + 1] != b'\n', f"Unexpected newline after chunk at offset {end}"
        off = end

