import os
import subprocess
import sys


def test_p_record_varints(tmp_path, monkeypatch):
    from pynytprof._pywrite import Writer
    monkeypatch.setattr(os, 'getpid',  lambda: 90)
    monkeypatch.setattr(os, 'getppid', lambda: 9000)
    out = tmp_path/'t.out'
    with Writer(out.open('wb')) as w:
        w.start_profile()
        w.end_profile()
    try:
        subprocess.run(
            ['perl', '-MDevel::NYTProf::Data', '-e',
             'Devel::NYTProf::Data::load_profile(@ARGV)', str(out)],
            check=True)
    except subprocess.CalledProcessError:
        import pytest
        pytest.skip('Devel::NYTProf::Data missing')
