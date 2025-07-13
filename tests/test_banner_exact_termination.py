import os
import subprocess
import sys
from pathlib import Path


def test_banner_ends_with_single_newline(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    idx = data.find(b"\nP")
    assert idx != -1, "Did not find \\nP"
    next_bytes = data[idx:idx+2]
    assert next_bytes == b"\nP", f"Expected exactly '\\nP', got {next_bytes}"
