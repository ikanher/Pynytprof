import os
import subprocess
import sys
from pathlib import Path


def test_active_writer_chunk_sequence(tmp_path, monkeypatch):
    out = tmp_path / "nytprof.out"
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
    tags = []
    off = idx
    while off < len(data):
        tok = data[off : off + 1]
        tags.append(tok)
        if tok == b"P":
            off += 1 + 4 + 16
            continue
        length = int.from_bytes(data[off + 1 : off + 5], "little")
        off += 5 + length
    assert tags == [b"P", b"S", b"D", b"C", b"E"], f"Got {tags!r}"
