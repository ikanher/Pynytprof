import subprocess, sys, os, re
from pathlib import Path
from tests.conftest import get_chunk_start

def test_no_blank_line_before_P(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.run([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env, check=True)
    data = out.read_bytes()
    p_off = get_chunk_start(data)
    # exactly one LF before 'P'
    assert data[p_off - 1] == 0x0A and data[p_off - 2] != 0x0A

