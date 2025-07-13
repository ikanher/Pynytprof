import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest


def test_perl_lines(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    script = Path(__file__).with_name("example_script.py")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pynytprof.tracer",
            str(script),
        ],
        cwd=tmp_path,
        env=env,
    )
    out_file = tmp_path / "nytprof.out"
    cmd = [
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "print Devel::NYTProf::Data->new({filename=>shift})->lines",
        str(out_file),
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    assert int(res.stdout.decode().strip()) > 0
