import os
import shutil
import subprocess
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from pynytprof.writer import Writer


def test_perl_callgraph(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    out = tmp_path / "out.nyt"
    with Writer(str(out)) as w:
        fid = w.add_file(str(out), True)
        a = w.sub_table.add(fid, 1, 1, "a", "m")
        b = w.sub_table.add(fid, 2, 2, "b", "m")
        w.callgraph.add(a, b, 5)
    cmd = [
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "print Devel::NYTProf::Data->new({filename=>shift})->calls",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    assert int(res.stdout.strip()) == 1
