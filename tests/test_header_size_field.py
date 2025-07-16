import os, subprocess, sys, re
from pathlib import Path
import pytest


@pytest.mark.parametrize("writer", ["py", "c"])
def test_header_size_points_to_P(tmp_path, writer):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": writer,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    if writer == "c":
        import importlib.util

        if importlib.util.find_spec("pynytprof._cwrite") is None:
            pytest.skip("_cwrite missing")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pynytprof.tracer",
            "-o",
            str(out),
            "-e",
            "pass",
        ],
        env=env,
    )
    data = out.read_bytes()
    header, _ = data.split(b"\n\n", 1)
    header_txt = header.decode()
    m = re.search(r":header_size=(\d+)", header_txt)
    assert m, "header_size line missing"
    declared = int(m.group(1))
    p_offset = len(header) + 2
    assert declared == p_offset, (
        f"header_size {declared} should equal P offset {p_offset}"
    )
