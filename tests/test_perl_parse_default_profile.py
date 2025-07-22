import os, subprocess, sys, shutil
from pathlib import Path
import pytest


def test_perl_parses_default_profile(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    script = Path(__file__).resolve().parents[1] / "tests" / "example_script.py"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
    )
    out_files = list(Path(tmp_path).glob("nytprof.out.*"))
    assert len(out_files) == 1
    prof = out_files[0]
    proc = subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data->new({ filename => shift, quiet => 1 })",
            str(prof),
        ],
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
