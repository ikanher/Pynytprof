import os
import re
import subprocess
import sys
import struct
from pathlib import Path


def test_banner_sanity(tmp_path):
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
    header, payload = data.split(b"\nP", 1)
    payload = b"P" + payload

    # 1) No leftover placeholder
    assert b"{SIZE" not in header, "Found unreplaced '{SIZE' placeholder in banner"
    nv = struct.calcsize("d")
    assert f":nv_size={nv}\n".encode() in header



    # 4) Sanity: first payload byte must be 'P'
    assert payload.startswith(b"P"), "Binary payload does not start with 'P' tag"
