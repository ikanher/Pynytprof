import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tests.utils import newest_profile_file, parse_nv_size_from_banner
from pynytprof.tags import NYTP_TAG_NEW_FID


def test_tracer_alignment_no_chunks(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYNYTPROF_DEBUG": "1",
        "PYNYTPROF_OUTER_CHUNKS": "0",
    }
    script = Path(__file__).with_name("example_script.py")
    proc = subprocess.run(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
        stderr=subprocess.PIPE,
    )
    out = newest_profile_file(tmp_path)
    data = out.read_bytes()
    banner_end = data.index(b"\nP")
    nv_size = parse_nv_size_from_banner(data)
    stream_off = banner_end + 1 + 1 + 4 + 4 + nv_size
    assert data[stream_off] not in {ord("S"), ord("F"), ord("D"), ord("C"), ord("E")}
    assert data[stream_off] == NYTP_TAG_NEW_FID

    stderr = proc.stderr.decode()
    first_token_offset = None
    expected = stream_off
    for line in stderr.splitlines():
        if line.startswith("DEBUG: first_token_offset="):
            first_token_offset = int(line.split("=")[1])
    assert first_token_offset == expected
