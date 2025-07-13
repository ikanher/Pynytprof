import os
import struct
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof import tracer


def test_s_offset_after_p(tmp_path):
    out = tmp_path / "nytprof.out"
    tracer.profile_command("pass", out_path=out)
    data = out.read_bytes()
    banner_end = data.index(b'!evals=0\n') + len(b'!evals=0\n')
    pid, ppid, ts = struct.unpack('<IId', data[banner_end+1+4:banner_end+1+4+16])
    expected_s_offset = banner_end + 1 + 4 + 16
    idx = data.index(b'S', banner_end)
    assert idx == expected_s_offset
