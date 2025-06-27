import os, shutil, subprocess, sys
from pathlib import Path
import pytest

HELLO = 'print("hello")\n'

def test_viewer_minimal(tmp_path):
    if not shutil.which("nytprofhtml"):
        pytest.skip("nytprofhtml missing")
    try:
        import pynytprof._tracer  # type: ignore
    except Exception:
        pytest.skip("_tracer missing")

    script = tmp_path / "hello.py"
    script.write_text(HELLO)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
    )

    subprocess.check_call(
        ["nytprofhtml", "-f", "nytprof.out", "-o", "report"],
        cwd=tmp_path,
    )

    assert (tmp_path / "report" / "index.html").exists()
