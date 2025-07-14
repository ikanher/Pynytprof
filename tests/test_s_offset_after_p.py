import struct
import os
import subprocess
import sys


def test_s_offset_after_p(tmp_path):
    out = tmp_path / "nytprof.out"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ])
    data = out.read_bytes()
    idx_p = data.index(b"\nP") + 1
    s_expected = idx_p + 1 + 4 + 16
    idx_s = data.index(b"S", s_expected - 1)
    assert idx_s == s_expected
