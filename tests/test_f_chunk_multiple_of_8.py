import os, subprocess, sys
from pathlib import Path
from tests.conftest import parse_chunks


def test_f_chunk_payload_multiple_of_8(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    chunks = parse_chunks(data)
    assert "F" in chunks
    assert chunks["F"]["length"] % 8 == 0, "F payload not multiple of 8 bytes"

