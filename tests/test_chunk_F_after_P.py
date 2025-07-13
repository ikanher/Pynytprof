import os
import subprocess
import sys
from pathlib import Path
def test_chunk_F_after_P(tmp_path, monkeypatch):
    out = tmp_path/'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYNTP_FORCE_PY': '1',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        'tests/example_script.py'
    ], env=env)
    data = out.read_bytes()
    i = data.index(b'\nP') + 1
    tags = []
    for _ in range(6):
        tags.append(data[i:i+1])
        length = int.from_bytes(data[i+1:i+5], 'little')
        i += 5 + length
    assert tags == [b'P', b'F', b'S', b'D', b'C', b'E']
