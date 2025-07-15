import os, subprocess, sys
from pathlib import Path


def test_pywrite_exact_sequence(tmp_path, monkeypatch):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYNYTPROF_DEBUG': '1',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    proc = subprocess.run(
        [sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'],
        env=env, stderr=subprocess.PIPE, text=True
    )
    data = out.read_bytes()
    idx = data.index(b'\n\nP') + 2
    tags = []
    seen = {}
    off = idx
    while off < len(data):
        tag = data[off:off+1]
        tags.append(tag)
        if tag == b'P':
            off += 1 + 4 + 4 + 8
            seen[tag] = seen.get(tag, 0) + 1
            continue
        length = int.from_bytes(data[off+1:off+5], 'little')
        seen[tag] = seen.get(tag, 0) + 1
        off += 5 + length
    assert tags == [b'P', b'S', b'D', b'C', b'E'], f"Tags: {tags!r}"
    assert seen[b'P'] == 1 and seen[b'S'] == 1 and seen[b'D'] == 1 and seen[b'C'] == 1 and seen[b'E'] == 1
    assert all(seen[t] == 1 for t in tags)
    assert all(l > 0 for t, l in seen.items() if t != b'E')

