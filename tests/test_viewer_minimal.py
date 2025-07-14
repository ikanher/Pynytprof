import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

HELLO = 'print("hello")\n'

def test_viewer_minimal(tmp_path):
    if not shutil.which("nytprofhtml"):
        pytest.skip("nytprofhtml missing")
    try:
        import pynytprof._ctrace  # type: ignore  # noqa: F401
    except Exception:
        pytest.skip("_ctrace missing")

    script = tmp_path / "hello.py"
    script.write_text(HELLO)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    out = tmp_path / f"nytprof.out.{os.getpid()}"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), str(script)],
        cwd=tmp_path,
        env=env,
    )

    subprocess.check_call(
        ["nytprofhtml", "-f", out.name, "-o", "report"],
        cwd=tmp_path,
    )

    assert (tmp_path / "report" / "index.html").exists()
