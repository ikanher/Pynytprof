import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.utils import newest_profile_file, parse_nv_size_from_banner

@pytest.mark.xfail(reason="outer chunks misalign stream")
def test_alignment_with_outer_chunks(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYNYTPROF_OUTER_CHUNKS": "1",
    }
    script = Path(__file__).with_name("example_script.py")
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
    )
    out = newest_profile_file(tmp_path)
    data = out.read_bytes()
    p_off = data.index(b"\nP") + 1
    nv_size = parse_nv_size_from_banner(data)
    stream_off = p_off + 1 + 4 + 4 + nv_size
    assert data[stream_off] in {ord("S"), ord("F"), ord("D"), ord("C"), ord("E")}

