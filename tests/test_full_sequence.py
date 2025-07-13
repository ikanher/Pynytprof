import os, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start

SCRIPT = 'tests/cg_example.py'


def _tokens(out):
    data = out.read_bytes()
    cutoff = get_chunk_start(data)
    toks = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        toks.append(tok)
        if tok == b'P':
            length = int.from_bytes(data[off+1:off+5], 'little')
            off += 5 + length
            continue
        length = int.from_bytes(data[off+1:off+5], 'little')
        off += 5 + length
    return b''.join(toks)


def test_full_sequence_py(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'py')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), SCRIPT])
    assert _tokens(out) == b'PSDCE'


def test_full_sequence_c(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'c')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), SCRIPT])
    assert _tokens(out) == b'PSDCE'
