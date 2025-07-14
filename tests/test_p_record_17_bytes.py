import os, subprocess, sys
from pathlib import Path
import pytest
from pynytprof._pywrite import _perl_nv_size


def test_p_record_is_21_bytes(tmp_path):
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
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    assert data[idx + 5 + 8 + _perl_nv_size() : idx + 5 + 8 + _perl_nv_size() + 1] == b"S"
