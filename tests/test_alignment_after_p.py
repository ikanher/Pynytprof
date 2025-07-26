import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from tests.utils import newest_profile_file
from pynytprof.reader import header_scan


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
    _, _, stream_off = header_scan(data)
    assert data[stream_off:stream_off + 1] == b"S"

