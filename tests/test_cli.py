import pytest
pytestmark = pytest.mark.legacy_psfdce
import os
import subprocess
from pathlib import Path
import pytest

CLI = Path(__file__).resolve().parents[1] / "pynytprof"
ENV = dict(os.environ)
ENV.setdefault("PYNYTPROF_OUTER_CHUNKS", "1")
ENV["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")


def test_help_shows_commands():
    res = subprocess.run([str(CLI), "--help"], text=True, capture_output=True, env=ENV)
    assert res.returncode == 0
    assert "profile" in res.stdout
    assert "verify" in res.stdout
    assert "html" in res.stdout
    assert "speedscope" in res.stdout


@pytest.mark.parametrize("writer", ["py", "c"])
def test_profile_verify(tmp_path, writer):
    script = Path(__file__).with_name("example_script.py")
    env = dict(ENV)
    if writer == "py":
        env["PYNTP_FORCE_PY"] = "1"
    env.setdefault("PYNYTPROF_OUTER_CHUNKS", "1")
    out_file = tmp_path / f"nytprof.out.{os.getpid()}"
    proc = subprocess.run([str(CLI), "profile", "-o", str(out_file), str(script)], cwd=tmp_path, env=env)
    assert proc.returncode == 0
    data = out_file.read_bytes()
    assert data.startswith(b"NYTProf 5 0\n")
    proc = subprocess.run(
        [str(CLI), "verify", out_file.name, "-q"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    perl = subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "exit !Devel::NYTProf::Data->new({filename=>shift})->blocks",
            out_file.name,
        ],
        cwd=tmp_path,
    )
    if perl.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    proc = subprocess.run(
        [str(CLI), "verify", out_file.name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "\u2713" in proc.stdout
    bad_data = data[:-5]
    out_file.write_bytes(bad_data)
    bad = subprocess.run([str(CLI), "verify", out_file.name], cwd=tmp_path, env=env)
    assert bad.returncode == 1


def test_exit_code_passthrough(tmp_path):
    script = tmp_path / "exitme.py"
    script.write_text("import sys; sys.exit(3)\n")
    out_file = tmp_path / f"nytprof.out.{os.getpid()}"
    proc = subprocess.run([
        str(CLI),
        "profile",
        "-o",
        str(out_file),
        str(script)
    ], cwd=tmp_path, env=ENV)
    assert proc.returncode == 3
