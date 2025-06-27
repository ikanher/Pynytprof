import os
import subprocess
import sys
from pathlib import Path


def test_verify(tmp_path):
    script = Path(__file__).with_name("example_script.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        str(script),
    ], cwd=tmp_path, env=env)
    out = tmp_path / "nytprof.out"
    proc = subprocess.run(
        [sys.executable, "-m", "pynytprof", "verify", "nytprof.out"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    assert "\u2713" in proc.stdout
    data = out.read_bytes()
    out.write_bytes(data[:-1] + bytes([data[-1] ^ 0xFF]))
    proc = subprocess.run(
        [sys.executable, "-m", "pynytprof", "verify", "nytprof.out"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 1
