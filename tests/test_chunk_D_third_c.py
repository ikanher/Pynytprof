import os, subprocess, sys
from pathlib import Path

def test_c_writer_emits_D_third(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'c')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/cg_example.py'])
    data = out.read_bytes()
    cutoff = data.index(b'\n\n') + 2
    tokens = []
    off = cutoff
    while off < len(data):
        tokens.append(data[off:off+1])
        length = int.from_bytes(data[off+1:off+5], 'little')
        off += 5 + length
    assert tokens[2] == b'D'
