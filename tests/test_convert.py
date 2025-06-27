import json
import os
import subprocess
import sys
from pathlib import Path


def test_convert(tmp_path):
    script = Path(__file__).with_name("example_script.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        str(script),
    ], cwd=tmp_path, env=env)
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof",
        "convert",
        "--speedscope",
        "nytprof.out",
    ], cwd=tmp_path, env=env)
    out_json = tmp_path / "nytprof.speedscope.json"
    data = json.loads(out_json.read_text())
    assert data["$schema"] == "https://www.speedscope.app/file-format-schema.json"
