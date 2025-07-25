import os, subprocess, sys
from pathlib import Path


def test_debug_chunk_summary(tmp_path):
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYNTP_FORCE_PY": "1",
        "PYNYTPROF_DEBUG": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert "P-rec  pid=" in proc.stderr
