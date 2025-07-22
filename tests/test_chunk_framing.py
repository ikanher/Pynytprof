import os
import subprocess
import sys
from pathlib import Path


def test_chunk_framing(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    pos = idx + 17  # skip raw P record
    while pos < len(data):
        tag = data[pos:pos + 1]
        pos += 1
        if tag in b"SFDC":
            length = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4 + length
        elif tag == b"E":
            assert pos == len(data), "E not at end of file"
            break
        else:
            raise AssertionError(f"unexpected tag {tag!r} at {pos-1}")
    else:
        raise AssertionError("missing E terminator")
