import os
import subprocess
import sys
from pathlib import Path

from tests.utils import newest_profile_file, parse_nv_size_from_banner
from pynytprof.tags import NYTP_TAG_NEW_FID
from pynytprof.protocol import read_u32, read_i32


def test_first_token_is_new_fid(tmp_path):
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

    banner_end = data.index(b"\nP")
    nv_size = parse_nv_size_from_banner(data)
    stream_off = banner_end + 1 + 1 + 4 + 4 + nv_size
    assert data[stream_off] == NYTP_TAG_NEW_FID

    off = stream_off + 1
    fid, off = read_u32(data, off)
    eval_fid, off = read_u32(data, off)
    eval_line, off = read_u32(data, off)
    flags, off = read_u32(data, off)
    size, off = read_u32(data, off)
    mtime, off = read_u32(data, off)
    name_len, off = read_i32(data, off)
    name = data[off : off + abs(name_len)]

    assert fid == 1
    assert eval_fid == 0
    assert eval_line == 0
    assert flags == 0
    assert size == 0
    assert mtime == 0
    assert name == b"(unknown)"
    assert name_len == len(b"(unknown)")

