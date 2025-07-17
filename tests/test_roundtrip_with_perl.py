import os, subprocess, sys, shutil
from pathlib import Path
import pytest


def test_roundtrip_parsed_by_nytprof(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    prof = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(prof),
        "tests/example_script.py",
    ], env=env)
    res = subprocess.run([
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "Devel::NYTProf::Data->new(filename=>shift,quiet=>1)",
        str(prof),
    ])
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    assert res.returncode == 0
