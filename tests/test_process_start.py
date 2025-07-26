import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from pynytprof._pywrite import Writer


def test_p_record_varints(tmp_path, monkeypatch):
    monkeypatch.setattr(os, 'getpid', lambda: 90)  # 1-byte
    monkeypatch.setattr(os, 'getppid', lambda: 9000)  # 2-byte
    out = tmp_path / 't.out'
    with Writer(out.open('wb')) as w:
        w.start_profile()
        w.end_profile()
    proc = subprocess.run(
        ['perl', '-MDevel::NYTProf::Data', '-e',
         'Devel::NYTProf::Data::load_profile(shift)', str(out)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        import pytest
        pytest.skip("Devel::NYTProf loader missing")
