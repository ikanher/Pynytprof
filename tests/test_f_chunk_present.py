import os, subprocess, sys, struct
from pathlib import Path
from tests.conftest import parse_chunks

def test_f_chunk_present(tmp_path):
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    data = out.read_bytes()
    chunks = parse_chunks(data)
    assert "F" in chunks, "Missing F chunk (file-handle definitions)"
    assert chunks["F"]["length"] >= 8
