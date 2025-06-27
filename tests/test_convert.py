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
    out_json = tmp_path / "out.json"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.main",
        "convert",
        "--speedscope",
        "nytprof.out",
        str(out_json),
    ], cwd=tmp_path, env=env)
    data = json.loads(out_json.read_text())
    assert data["schema"]
    assert data["version"] == "0.3.0"
    assert data["profiles"]
    events = data["profiles"][0]["events"]
    assert any(e["type"] == "O" for e in events)
    assert any(e["type"] == "C" for e in events)
