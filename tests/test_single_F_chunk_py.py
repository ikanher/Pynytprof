import pytest
pytestmark = pytest.mark.legacy_psfdce
import os, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start


def test_one_F_chunk(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER', 'py')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'])
    data = out.read_bytes()
    cutoff = get_chunk_start(data)
    tags = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        tags.append(tok)
        if tok == b'P':
            off += 17
            continue
        length = int.from_bytes(data[off+1:off+5], 'little')
        off += 5 + length
    f_positions = [i for i, t in enumerate(tags) if t == b'F']
    assert f_positions == [2], f'Unexpected F chunk positions: {f_positions}'

