import pytest
pytestmark = pytest.mark.legacy_psfdce
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
    tags = []
    lines = proc.stderr.splitlines()
    for line in lines:
        if line.startswith("DEBUG: wrote raw P record"):
            tags.append('P')
            continue
        if m := pattern.search(line):
            tags.append(m.group(1))
    if lines and lines[-1].startswith("DEBUG: about to write raw data") and lines[-1].endswith("=1"):
        tags.append('E')
    assert tags == ['P', 'S', 'F', 'D', 'C', 'E']
