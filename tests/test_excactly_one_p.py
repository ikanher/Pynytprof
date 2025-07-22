from tests.conftest import get_chunk_start
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
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b'P'
    pid_bytes = data[idx+5:idx+9]
    assert pid_bytes == p.pid.to_bytes(4, 'little')
    s_off = data.index(b'S', idx + 21)
    assert s_off == idx + 21

