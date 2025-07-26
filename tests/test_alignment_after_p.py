import os
import subprocess
import sys
from pathlib import Path

from tests.utils import newest_profile_file, parse_nv_size_from_banner


def test_alignment_after_p(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
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
    assert data[stream_off:stream_off + 1] == b"@"

