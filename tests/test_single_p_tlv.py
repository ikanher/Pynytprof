import struct, os, subprocess, sys
from pathlib import Path


def test_single_p_tlv(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env)
    data = out.read_bytes()
    occurrences = [i for i in range(len(data)) if data[i:i+5] == b"P\x10\x00\x00\x00"]
    assert len(occurrences) == 1, f"Expected exactly one P TLV, found {len(occurrences)}"
