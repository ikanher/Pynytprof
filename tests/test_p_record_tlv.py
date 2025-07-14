import os
import subprocess
import sys
from pathlib import Path
import pytest


def test_p_record_tlv(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+5] == b"P" + (16).to_bytes(4, "little")
    assert data[idx+21:idx+22] == b"S"
