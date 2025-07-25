import pytest
pytestmark = pytest.mark.legacy_psfdce
def test_chunk_layout_is_tag_len_payload(tmp_path):
    import os, subprocess, sys
    from pathlib import Path

    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    script = Path(__file__).resolve().parents[1] / 'tests' / 'example_script.py'
    subprocess.check_call([
        sys.executable,
        '-m', 'pynytprof.tracer',
        '-o', str(out),
        str(script)
    ], env=env)

    data = out.read_bytes()
    off = data.index(b'\nP') + 1
    assert data[off:off+1] == b'P'
    off += 17
    for tag in (b'S', b'F', b'D', b'C'):
        assert data[off:off+1] == tag, f'expected {tag!r} at {off:#x}'
        ln = int.from_bytes(data[off+1:off+5], 'little')
        assert ln > 0
        off += 5 + ln
    assert data[off:off+1] == b'E'
    off += 1
    assert off == len(data), 'extra bytes after E'
