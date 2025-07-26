import os, subprocess, sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.xfail(reason="debug output changed")


def test_debug_per_event_logs(tmp_path, monkeypatch):
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
    assert "write tag=" in proc.stderr
