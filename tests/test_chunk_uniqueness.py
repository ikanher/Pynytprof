import os
import sys
import subprocess
import re
from pathlib import Path
import pytest


def test_chunk_uniqueness(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYNTP_FORCE_PY": "1",
        "PYNYTPROF_DEBUG": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    pattern = re.compile(r"^DEBUG: write tag=(\w) len=(\d+)")
    tags = [m.group(1) for line in proc.stderr.splitlines() if (m := pattern.search(line))]
    assert tags == ['P', 'S', 'D', 'C', 'E']
