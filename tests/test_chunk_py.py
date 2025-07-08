from pathlib import Path, PurePosixPath
import subprocess, os, sys


def test_py_writer_chunks(tmp_path):
    out = tmp_path/'p.out'
    subprocess.check_call([
        sys.executable,
        '-m','pynytprof.tracer',
        '-o',str(out),
        '-e','pass'
    ], env={**os.environ,'PYNYTPROF_WRITER':'py','PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')})
    data = out.read_bytes()
    hdr_end = 0
    for _ in range(10):
        hdr_end = data.index(b'\n', hdr_end) + 1
    token = data[hdr_end:hdr_end+1]
    length = int.from_bytes(data[hdr_end+1:hdr_end+5],'little')
    assert token in b'AF'
    assert b"A" in data
    a_pos = data.index(b"A")
    a_len = int.from_bytes(data[a_pos+1:a_pos+5],'little')
    assert data[a_pos+5 + a_len - 1] == 0
    assert data.endswith(b'E\x00\x00\x00\x00')
