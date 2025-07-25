import os
import subprocess
import sys
from pathlib import Path

from pynytprof.reader import header_scan
from pynytprof.tags import NYTP_TAG_NEW_FID
from tests.utils import newest_profile_file, parse_nv_size_from_banner


def test_header_scan_matches_perl(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYNYTPROF_OUTER_CHUNKS": "0",
    }
    script = Path(__file__).with_name("example_script.py")
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
    )
    out = newest_profile_file(tmp_path)
    data = out.read_bytes()
    header_len, p_pos, first_token_off = header_scan(data)
    assert data[first_token_off] == NYTP_TAG_NEW_FID
    nv_size = parse_nv_size_from_banner(data)
    assert first_token_off == p_pos + 1 + 4 + 4 + nv_size

    last_nl = data.rfind(b"\n", 0, p_pos)
    bad = [(last_nl + 1 + i, b) for i, b in enumerate(data[last_nl + 1 : p_pos]) if b >= 0x80]
    assert not bad, f"high bytes before P: {bad}"
