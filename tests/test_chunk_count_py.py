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
    cutoff = data.index(b'\n\n')+2
    tags = []
    off = cutoff
    while off < len(data):
        tags.append(data[off:off+1])
        length = int.from_bytes(data[off+1:off+5],'little')
        off += 5 + length
    assert tags == [b'F',b'S',b'D',b'C',b'E'], f"Got {tags!r}"
