import os
import subprocess
import sys
from pathlib import Path
import pytest

def test_no_buffered_P_chunk(tmp_path):
    out = tmp_path / "nytprof.out"
    log = tmp_path / "nytprof.log"
    env = {
        **os.environ,
        "PYNYTPROF_DEBUG": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    with log.open("w") as fh:
        subprocess.check_call(
            [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
            env=env,
            stderr=fh,
        )
    logs = log.read_text()
    assert "buffering chunk tag=P" not in logs, f"Found buffered P chunk in logs: {logs}"

