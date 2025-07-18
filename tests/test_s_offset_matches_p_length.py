# tests/test_s_offset_matches_p_length.py
import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.conftest import parse_chunks

def test_s_offset_matches_p_chunk_length(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([
        sys.executable, "-m", "pynytprof.tracer",
        "-o", str(out), "-e", "pass",
    ], env=env)
    data = out.read_bytes()
    chunks = parse_chunks(data)
    assert 'P' in chunks and 'S' in chunks, "Missing P or S chunk"
    p_off = chunks['P']['offset']
    p_len = chunks['P']['length']
    s_off = chunks['S']['offset']
    expected = p_off + 1 + p_len
    assert s_off == expected, f"S offset {s_off:#x} != expected {expected:#x}"
