import os, subprocess, sys
from pathlib import Path


def test_exactly_two_lf_before_p(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {**os.environ,
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    p = subprocess.Popen([sys.executable, "-m", "pynytprof.tracer",
                          "-o", str(out), "-e", "pass"], env=env)
    p.wait()
    data = out.read_bytes()
    idx_p = data.index(b'\n\nP') + 2  # start of raw P record
    # Count consecutive LF bytes immediately before 'P'
    lf_count = 0
    i = idx_p - 1
    while data[i] == 0x0A:
        lf_count += 1
        i -= 1
    assert lf_count == 2, (
        f"expected exactly 2 LF before 'P', found {lf_count}"
    )
    # First 4 payload bytes must be the real PID, not length=16
    pid = int.from_bytes(data[idx_p+1:idx_p+5], 'little')
    assert pid == p.pid, "still writing length word after 'P'"
