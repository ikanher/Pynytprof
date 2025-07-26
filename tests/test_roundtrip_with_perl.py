import os
import subprocess
import shutil
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_roundtrip_with_perl(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    out = tmp_path / "nytprof.out"
    with Writer(str(out)) as w:
        w.start_profile()
        w.end_profile()
    res = subprocess.run([
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "Devel::NYTProf::Data::load_profile(shift)",
        str(out),
    ])
    if res.returncode != 0:
        pytest.skip("NYTProf not installed")
    assert res.returncode == 0
