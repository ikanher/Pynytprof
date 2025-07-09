import os, subprocess, sys
from pathlib import Path

def test_c_writer_emits_F_first(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'c')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/cg_example.py'])
    data = out.read_bytes()
    cutoff = data.index(b'\n\n') + 2
    assert data[cutoff:cutoff+1] == b'F'
