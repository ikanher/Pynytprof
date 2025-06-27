import os
import subprocess
import sys
from pathlib import Path
import shutil
import pytest


@pytest.mark.parametrize("force_py", [False, True])
def test_callgraph(tmp_path, force_py):
    script = Path(__file__).with_name("cg_example.py")
    if not shutil.which("nytprofhtml"):
        pytest.skip("nytprofhtml missing")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if force_py:
        env["PYNTP_FORCE_PY"] = "1"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        str(script),
    ], cwd=tmp_path, env=env)
    try:
        subprocess.check_call(["nytprofhtml", "-f", "nytprof.out"], cwd=tmp_path)
    except Exception:
        with open(tmp_path / "nytprof.out", "rb") as fh:
            print("HDR", fh.read(25).hex(), file=sys.stderr)
        raise
    html = (tmp_path / "nytprof" / "index.html").read_text()
    assert "cg_example.py->foo" in html
