import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pynytprof import reader

SCRIPT = Path(__file__).with_name("example_script.py")


def run(filter_val, tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["NYTPROF_FILTER"] = filter_val
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pynytprof.tracer",
            str(SCRIPT),
        ],
        cwd=tmp_path,
        env=env,
    )
    out = tmp_path / "nytprof.out"
    return reader.read(str(out))


def test_filter_excludes(tmp_path):
    data = run("nonexistent/*", tmp_path)
    assert not data["records"]


def test_filter_includes(tmp_path):
    data = run("*example_script.py", tmp_path)
    assert data["records"]
