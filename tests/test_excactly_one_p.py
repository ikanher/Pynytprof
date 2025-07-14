import subprocess, sys, struct, os, tempfile, pathlib

def test_exactly_one_p_record(tmp_path):
    out = tmp_path/"nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(pathlib.Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    p.wait()
    data = out.read_bytes()
    idx = data.index(b'\nP') + 1
    assert data[idx:idx+1] == b'P'
    pid_bytes = data[idx+1:idx+5]
    assert pid_bytes == p.pid.to_bytes(4, 'little')
    s_off = data.index(b'S')
    assert s_off == idx + 17
