from tests.conftest import get_chunk_start, parse_chunks
import os, subprocess, sys, struct
from pathlib import Path


def test_only_one_p_record_and_no_length(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    p = subprocess.Popen([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        "-e",
        "pass",
    ], env=env)
    p.wait()
    data = out.read_bytes()
    idx = get_chunk_start(data)
    chunks = parse_chunks(data[idx:])
    assert list(chunks.keys())[0] == "P" and len(chunks) >= 1
    assert chunks["P"]["offset"] == 0
    pid = int.from_bytes(chunks["P"]["payload"][:4], "little")
    assert pid == p.pid, "P chunk still has length word!"

