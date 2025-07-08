import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("writer", ["py"])  # only python writer needed
def test_exc_ticks(tmp_path, writer):
    script = Path(__file__).with_name("example_script.py")
    out = tmp_path / "out.nyt"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYNTP_FORCE_PY": "1",
        "PYNYTPROF_WRITER": writer,
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), str(script)],
        env=env,
    )
    data = out.read_bytes()
    s_pos = data.index(b"S")
    slen = struct.unpack_from("<I", data, s_pos + 1)[0]
    payload = data[s_pos + 5 : s_pos + 5 + slen]
    rec_size = struct.calcsize("<IIIQQ")
    found = False
    for off in range(0, len(payload), rec_size):
        _, line, calls, inc, exc = struct.unpack_from("<IIIQQ", payload, off)
        if exc > 0:
            assert exc <= inc
            found = True
            break
    assert found
