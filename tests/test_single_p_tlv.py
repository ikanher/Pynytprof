import struct
import os
import subprocess
import sys
from pathlib import Path


def test_only_one_p_record(tmp_path):
    out = tmp_path/"nytprof.out"
    subprocess.check_call([
        sys.executable, "-m", "pynytprof.tracer",
        "-o", str(out), "-e", "pass"
    ])
    data = out.read_bytes()
    hdr = b"P" + (16).to_bytes(4, "little")
    occurrences = [i for i in range(len(data)-4) if data[i:i+5] == hdr]
    assert len(occurrences) == 1, f"Expected one P TLV, found {len(occurrences)}"
