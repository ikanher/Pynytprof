import subprocess, sys, os, struct
from pathlib import Path


import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_schunk(tmp_path, writer):
    out = tmp_path / "out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": writer,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
    )
    data = out.read_bytes()
    s_pos = data.index(b"S")
    slen = struct.unpack_from("<I", data, s_pos + 1)[0]
    assert slen % 28 == 0 and slen > 0
    offset = s_pos + 5
    rec_inc = int.from_bytes(data[offset + 12 : offset + 20], "little")
    assert rec_inc > 0
