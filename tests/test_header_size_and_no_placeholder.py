import os
import re
import subprocess
import sys
from pathlib import Path


def test_header_size_and_no_placeholder(tmp_path):
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
    m = re.search(rb":header_size=(\d+)\n", data)
    assert m, "Missing ':header_size=' line in banner"
    declared = int(m.group(1))
    header = data[:declared]
    payload = data[declared:]

    # 1) No leftover placeholder
    assert b"{SIZE" not in header, "Found unreplaced '{SIZE' placeholder in banner"

    # banner length should equal declared header_size
    actual = len(header)
    assert declared == actual, (
        f"header_size={declared}, but header length={actual}"
    )

    # 4) Sanity: first payload byte must be 'P'
    assert payload.startswith(b"P"), "Binary payload does not start with 'P' tag"
