import os
import subprocess
import sys
from pathlib import Path


def test_banner_ends_with_two_newlines(tmp_path):
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
    idx = data.find(b"\n\n")
    assert idx != -1, "Did not find \\n\\n"
    next_bytes = data[idx:idx+3]
    assert next_bytes == b"\n\nP", f"Expected exactly '\\n\\nP', got {next_bytes}"
