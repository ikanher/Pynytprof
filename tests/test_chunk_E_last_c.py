import os, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start

def test_c_writer_emits_E_last(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'c')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/cg_example.py'])
    data = out.read_bytes()
    cutoff = get_chunk_start(data)
    tokens = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        tokens.append(tok)
        if tok == b'P':
            off += 1 + 4 + 16
            continue
        length = int.from_bytes(data[off+1:off+5], 'little')
        off += 5 + length
    assert tokens[-1] == b'E'
    assert tokens == [b'P', b'S', b'D', b'C', b'E']
