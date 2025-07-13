import os, subprocess, sys
from pathlib import Path

def test_S_and_D_non_empty(tmp_path, monkeypatch):
    out = tmp_path/'nytprof.out'
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
    )
    data = out.read_bytes()
    idx = data.index(b"\nP") + 1
    seen = {}
    off = idx
    while off < len(data):
        tag = data[off:off+1]
        if tag == b"P":
            seen[tag] = 16
            off += 17
            continue
        length = int.from_bytes(data[off+1:off+5], "little")
        seen[tag] = length
        off += 5 + length
    assert seen[b"S"] > 0, f"S length {seen[b'S']}"
    assert seen[b"D"] > 0, f"D length {seen[b'D']}"

