import os, subprocess, sys

def test_no_newline_bytes_after_header(tmp_path):
    out = tmp_path/'nytprof.out'
    env = {**os.environ, 'PYNYTPROF_WRITER':'py'}
    subprocess.check_call(
        [sys.executable, '-m', 'pynytprof.tracer', '-o', str(out), 'tests/example_script.py'],
        env=env
    )
    data = out.read_bytes()
    split = data.index(b'\n\n') + 2
    tail = data[split:]
    # Assert no 0x0A anywhere in the binary section
    pos = tail.find(b'\n')
    assert pos == -1, f"Found newline in payload at offset {split + pos}"
