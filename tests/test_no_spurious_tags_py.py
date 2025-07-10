import os, subprocess, sys
from pathlib import Path


def _chunk_tags(data):
    cutoff = data.index(b"\n\n") + 2
    tags = []
    off = cutoff
    while off < len(data):
        tag = data[off:off+1]
        tags.append(tag)
        length = int.from_bytes(data[off+1:off+5], "little")
        off += 5 + length
    return tags


def test_no_spurious_tags(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    tags = _chunk_tags(data)
    assert tags == [b"F", b"S", b"D", b"C", b"E"], tags
