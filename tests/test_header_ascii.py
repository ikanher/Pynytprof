import os
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_ascii_header(tmp_path, writer):
    env = os.environ.copy()
    env["PYNYTPROF_WRITER"] = writer
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    out = tmp_path / "prof.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    assert data.startswith(b"NYTProf 5 0\n")
    assert b"\0" not in data[:1024]
