import os, subprocess, sys, re
from pathlib import Path
import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_banner_ends_at_first_P(tmp_path, writer):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": writer,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    if writer == "c":
        import importlib.util

        if importlib.util.find_spec("pynytprof._cwrite") is None:
            pytest.skip("_cwrite missing")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pynytprof.tracer",
            "-o",
            str(out),
            "-e",
            "pass",
        ],
        env=env,
    )
    data = out.read_bytes()
    p_off = data.index(b"\nP") + 1
    assert data[p_off:p_off + 1] == b"P"
