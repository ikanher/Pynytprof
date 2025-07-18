from tests.conftest import get_chunk_start
import os, subprocess, sys
from pathlib import Path


def test_only_five_top_level_chunks(tmp_path, monkeypatch):
    out = tmp_path/'nytprof.out'
    monkeypatch.setenv('PYNYTPROF_WRITER','py')
    monkeypatch.setenv('PYNTP_FORCE_PY', '1')
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).resolve().parents[1] / 'src'))
    subprocess.check_call([
        sys.executable,
        '-m','pynytprof.tracer',
        '-o', str(out),
        'tests/example_script.py'
    ])
    data = out.read_bytes()
    cutoff = get_chunk_start(data)
    tags = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        tags.append(tok)
        if tok == b'P':
            length = int.from_bytes(data[off+1:off+5],'little')
            off += 5 + length
            continue
        length = int.from_bytes(data[off+1:off+5],'little')
        off += 5 + length
    assert tags == [b'P', b'S', b'F', b'D', b'C', b'E'], f"Got {tags!r}"

