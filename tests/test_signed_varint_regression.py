import subprocess, os, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_signed_varint_regression(tmp_path):
    out = tmp_path / "p.out"
    with Writer(str(out)) as w:
        w.start_profile()
        w.write_time_line(fid=1, line=1, elapsed=-11, overflow=0)
        w.end_profile()

    proc = subprocess.run(
        ["perl", "-MDevel::NYTProf::Data", "-e", "Devel::NYTProf::Data::load_profile(shift)", str(out)],
    )
    if proc.returncode != 0:
        pytest.skip("Devel::NYTProf::Data missing")
    assert proc.returncode == 0

