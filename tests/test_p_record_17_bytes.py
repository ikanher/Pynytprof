import struct
import subprocess, os, sys
from pathlib import Path


def test_p_record_17_bytes(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
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
    assert data[idx] == 0x50
    pid, ppid, ts = struct.unpack("<II", data[idx+1:idx+9]) + (
        struct.unpack("<d", data[idx+9:idx+17])[0],
    )
    assert idx + 17 == data.index(b"S", idx)
