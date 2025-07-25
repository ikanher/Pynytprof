import pytest
pytestmark = pytest.mark.legacy_psfdce
from tests.conftest import get_chunk_start
from pathlib import Path, PurePosixPath
import subprocess, os, sys, struct


def test_py_writer_chunks(tmp_path):
    out = tmp_path / "p.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env={
            **os.environ,
            "PYNYTPROF_WRITER": "py",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        },
    )
    data = out.read_bytes()
    end = get_chunk_start(data)
    chunks = data[end:]
    tokens = []
    off = 0
    while off < len(chunks):
        tok = chunks[off:off+1]
        tokens.append(tok)
        if tok == b"P":
            off += 17
            continue
        length = int.from_bytes(chunks[off+1:off+5], "little")
        off += 5 + length
    assert tokens == [b"P", b"S", b"F", b"D", b"C", b"E"]
    assert b"A" not in tokens
    assert data.endswith(b"E")

