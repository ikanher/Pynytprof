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
    header, _ = data.split(b"\nP", 1)
    assert b":nv_size=8\n" in header
    m = re.search(rb":header_size=(\d+)", header)
    asserted = int(m.group(1))
    first_p = data.index(b"P", asserted)
    assert asserted == first_p, f"header_size {asserted} != P offset {first_p}"
