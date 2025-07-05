import os
import subprocess
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "pynytprof"
ENV = dict(os.environ)
ENV["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")


def test_help_shows_commands():
    res = subprocess.run([str(CLI), "--help"], text=True, capture_output=True, env=ENV)
    assert res.returncode == 0
    assert "profile" in res.stdout
    assert "verify" in res.stdout
    assert "html" in res.stdout
    assert "speedscope" in res.stdout


def test_profile_verify(tmp_path):
    script = Path(__file__).with_name("example_script.py")
    proc = subprocess.run([str(CLI), "profile", str(script)], cwd=tmp_path, env=ENV)
    assert proc.returncode == 0
    proc = subprocess.run(
        [str(CLI), "verify", "nytprof.out", "-q"],
        cwd=tmp_path,
        env=ENV,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    proc = subprocess.run(
        [str(CLI), "verify", "nytprof.out"],
        cwd=tmp_path,
        env=ENV,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "\u2713" in proc.stdout
    out_file = tmp_path / "nytprof.out"
    data = out_file.read_bytes()
    out_file.write_bytes(data[:-5])
    bad = subprocess.run([str(CLI), "verify", "nytprof.out"], cwd=tmp_path, env=ENV)
    assert bad.returncode == 1


def test_exit_code_passthrough(tmp_path):
    script = tmp_path / "exitme.py"
    script.write_text("import sys; sys.exit(3)\n")
    proc = subprocess.run([str(CLI), "profile", str(script)], cwd=tmp_path, env=ENV)
    assert proc.returncode == 3
