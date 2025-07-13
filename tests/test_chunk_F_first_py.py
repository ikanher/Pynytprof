import os, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start

def test_py_writer_emits_P_first(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'py')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/cg_example.py'])
    data = out.read_bytes()
    cutoff = get_chunk_start(data)
    assert data[cutoff:cutoff+1] == b'P'
