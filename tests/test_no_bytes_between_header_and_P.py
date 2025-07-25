import os
import subprocess
import sys
from pathlib import Path


def test_no_bytes_between_header_and_P(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
    )
    data = out.read_bytes()
    banner_end = data.index(b"\nP")
    assert data[banner_end] == 0x0A
    assert data[banner_end + 1] == ord("P")
