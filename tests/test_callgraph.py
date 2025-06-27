import os
import subprocess
import sys
from pathlib import Path
import shutil
import pytest


def test_callgraph(tmp_path):
    script = Path(__file__).with_name("cg_example.py")
    if not shutil.which("nytprofhtml"):
        pytest.skip("nytprofhtml missing")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        str(script),
    ], cwd=tmp_path, env=env)
    with open(tmp_path / 'nytprof.out', 'rb') as fh:
        print("HDR", fh.read(16).hex(), file=sys.stderr)
    subprocess.check_call(["nytprofhtml", "-f", "nytprof.out"], cwd=tmp_path)
    html = (tmp_path / "nytprof" / "index.html").read_text()
    assert "cg_example.py->foo" in html
