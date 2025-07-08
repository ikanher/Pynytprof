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
    if writer == "c":
        import importlib.util

        if importlib.util.find_spec("pynytprof._cwrite") is None:
            pytest.skip("_cwrite missing")
    out = tmp_path / "out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env
    )
    data = out.read_bytes()
    assert data.startswith(b"NYTProf 5 0\n")
    hdr_end = data.index(b"\n", data.index(b"\n", data.index(b"\n") + 1) + 1) + 1
    assert b"\0" not in data[:hdr_end]
    assert b"A" not in data.split(b"\n\n", 1)[1][:32]  # no A in first chunk
