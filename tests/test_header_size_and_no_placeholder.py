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

    # Split into header (text) and payload (binary)
    try:
        header, payload = data.split(b"\n\n", 1)
    except ValueError:
        pytest.fail("Did not find the blank-line delimiter '\\n\\n' in output")

    # 1) No leftover placeholder
    assert b"{SIZE" not in header, "Found unreplaced '{SIZE' placeholder in banner"

    # 2) Extract declared header_size
    m = re.search(rb"^:header_size=(\d+)$", header, re.MULTILINE)
    assert m, "Missing ':header_size=' line in banner"
    declared = int(m.group(1))

    # 3) header_size must equal the byte offset of the 'P' tag
    p_offset = len(header) + 2
    assert declared == p_offset, (
        f"Declared header_size={declared} but first 'P' is at {p_offset}"
    )

    # 4) Sanity: first payload byte must be 'P'
    assert payload.startswith(b"P"), "Binary payload does not start with 'P' tag"
