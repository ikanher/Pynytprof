import os, subprocess, sys
from pathlib import Path
from tests.conftest import get_chunk_start
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof.protocol import read_u32


def test_exactly_two_lf_before_p(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {**os.environ,
           "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    p = subprocess.Popen([sys.executable, "-m", "pynytprof.tracer",
                          "-o", str(out), "-e", "pass"], env=env)
    p.wait()
    data = out.read_bytes()
    idx_p = get_chunk_start(data)  # start of raw P record
    # Count consecutive LF bytes immediately before 'P'
    lf_count = 0
    i = idx_p - 1
    while data[i] == 0x0A:
        lf_count += 1
        i -= 1
    assert lf_count == 1, (
        f"expected exactly 1 LF before 'P', found {lf_count}"
    )
    pid, _ = read_u32(data, idx_p + 1)
    assert pid == p.pid, "PID not at expected offset"
