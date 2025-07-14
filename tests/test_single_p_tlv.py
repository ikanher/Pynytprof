import os
import subprocess
import sys
from pathlib import Path


def test_only_one_p_record(tmp_path):
    out = tmp_path/"nytprof.out"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen([
        sys.executable, "-m", "pynytprof.tracer",
        "-o", str(out), "-e", "pass"
    ], env=env)
    p.wait()
    data = out.read_bytes()
    length16 = (16).to_bytes(4, "little")
    occurrences = [
        i for i in range(len(data) - 5) if data[i : i + 5] == b"P" + length16
    ]
    assert len(occurrences) == 1, f"Expected one P TLV, found {len(occurrences)}"
