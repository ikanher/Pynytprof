import subprocess, sys, os, struct
from pathlib import Path


import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_schunk(tmp_path, writer):
    out = tmp_path / "out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": writer,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
    )
    data = out.read_bytes()
    end = data.index(b"\nP") + 1
    chunks = data[end:]
    tokens = []
    off = 0
    s_off = None
    while off < len(chunks):
        tok = chunks[off : off + 1]
        tokens.append(tok)
        length = int.from_bytes(chunks[off + 1 : off + 5], "little")
        if tok == b"S":
            s_off = off
        off += 5 + length
    assert tokens == [b"P", b"S", b"D", b"C", b"E"]
    assert s_off is not None
    slen = int.from_bytes(chunks[s_off + 1 : s_off + 5], "little")
    assert slen % 28 == 0 and slen > 0
