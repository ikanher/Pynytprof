import os
import subprocess
import sys
from pathlib import Path
import pytest
from tests.conftest import get_chunk_start


@pytest.mark.parametrize("writer", ["py", "c"])
def test_ascii_header(tmp_path, writer):
    env = os.environ.copy()
    env["PYNYTPROF_WRITER"] = writer
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    out = tmp_path / "prof.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env=env,
    )
    data = out.read_bytes()
    assert data.startswith(b"NYTProf 5 0\n")
    hdr_end = data.index(b"\n", data.index(b"\n", data.index(b"\n") + 1) + 1) + 1
    assert b"\0" not in data[:hdr_end]
    cutoff = get_chunk_start(data)
    assert data[cutoff:cutoff + 1] == b"F"


def test_header_banner(tmp_path):
    """ensure both writer implementations start with an ASCII banner"""
    out = tmp_path / "hdr.out"
    for writer in ["py", "c"]:
        env = {
            "PYNYTPROF_WRITER": writer,
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        }
        subprocess.check_call(
            [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
            env=env,
        )
        assert out.read_bytes().startswith(b"NYTProf 5 0\n")


def test_writer_modes(tmp_path):
    """Both explicit modes produce an ASCII banner"""
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    out = tmp_path / "out.nyt"
    for wr in ["py", "c"]:
        env["PYNYTPROF_WRITER"] = wr
        subprocess.check_call(
            [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
            env=env,
        )
        data = out.read_bytes()
        assert data.startswith(b"NYTProf 5 0\n")
