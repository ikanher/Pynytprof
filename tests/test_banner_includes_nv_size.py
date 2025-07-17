import os
import subprocess
import sys
import re
from pathlib import Path


def test_banner_includes_nv_size(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    header = data.split(b"\nP", 1)[0].decode()
    assert ":nv_size=8\n" in header, "Banner missing ':nv_size=8' line"
