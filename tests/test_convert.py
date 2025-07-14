import json
import os
import subprocess
import sys
from pathlib import Path


def test_convert(tmp_path):
    script = Path(__file__).with_name("example_script.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    out_file = tmp_path / f"nytprof.out.{os.getpid()}"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out_file),
        str(script),
    ], cwd=tmp_path, env=env)
    out_json = tmp_path / "nytprof.speedscope.json"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof",
        "speedscope",
        out_file.name,
        "--out",
        str(out_json),
    ], cwd=tmp_path, env=env)
    data = json.loads(out_json.read_text())
    assert data["$schema"] == "https://www.speedscope.app/file-format-schema.json"
