import os
import subprocess
import sys
from pathlib import Path
import shutil
import pytest


@pytest.mark.xfail(reason="roundtrip fails until NV size fix")
def test_nytprof_roundtrip(tmp_path):
    script = Path(__file__).with_name("example_script.py")
    out_file = tmp_path / "nytprof.out"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    res = subprocess.run(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out_file), str(script)],
        cwd=tmp_path,
        env=env,
    )
    assert res.returncode == 0
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    perl = subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data->new({filename=>$ARGV[0], quiet=>1})",
            str(out_file),
        ],
        cwd=tmp_path,
    )
    assert perl.returncode == 0

