import os, subprocess, sys
from pathlib import Path
import pytest


def test_p_record_is_17_bytes(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env
    )
    data = out.read_bytes()
    idx = data.index(b"\n\nP") + 2
    assert data[idx:idx+1] == b"P"
    assert data[idx + 17 : idx + 18] == b"S"

