import os
import subprocess
import sys
from pathlib import Path


def test_no_spurious_tags(tmp_path, monkeypatch):
    out = tmp_path / "nytprof.out"
    monkeypatch.setenv("PYNYTPROF_WRITER", "py")
    monkeypatch.setenv(
        "PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src")
    )
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pynytprof.tracer",
            "-o",
            str(out),
            "tests/example_script.py",
        ],
        env=os.environ,
    )
    data = out.read_bytes()
    idx = data.index(b"\n\n") + 2
    tags = []
    off = idx
    while off < len(data):
        tag = data[off : off + 1]
        tags.append(tag)
        length = int.from_bytes(data[off + 1 : off + 5], "little")
        off += 5 + length

    assert tags == [b"F", b"S", b"D", b"C", b"E"], f"Found spurious tags: {tags!r}"
