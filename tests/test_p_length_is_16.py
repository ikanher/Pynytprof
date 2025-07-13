import os
import subprocess
import sys
from pathlib import Path
import importlib.util
import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_p_length_is_16(tmp_path, writer):
    env = os.environ.copy()
    env["PYNYTPROF_WRITER"] = writer
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if writer == "c" and importlib.util.find_spec("pynytprof._cwrite") is None:
        pytest.skip("_cwrite missing")
    out = tmp_path / "nytprof.out"
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
    hdr = data[idx:idx + 5]
    assert hdr == b"P\x10\x00\x00\x00"
