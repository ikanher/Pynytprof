import os, subprocess, sys

def test_p_record_is_17_bytes(tmp_path):
    out = tmp_path/"nytprof.out"
    env = {**os.environ, "PYNYTPROF_WRITER": "py"}
    subprocess.check_call([
        sys.executable,
        "-m", "pynytprof.tracer",
        "-o", str(out), "-e", "pass"
    ], env=env)
    data = out.read_bytes()
    idx = data.index(b'\nP') + 1
    payload = data[idx+1:idx+17]
    assert len(payload) == 16
    assert data[idx+17:idx+18] == b'S'

