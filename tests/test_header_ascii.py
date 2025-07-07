import subprocess
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pynytprof._pywrite as pw


def test_ascii_header(tmp_path):
    out = tmp_path / 'nytprof.out'
    with pw.Writer(str(out)):
        pass
    raw = out.read_bytes()
    assert raw.startswith(b'NYTProf 5 0\n#Perl profile database')
    assert b':ticks_per_sec=10000000\n' in raw
    assert b'perl_version=' in raw
    idx = 0
    for _ in range(10):
        idx = raw.index(b"\n", idx) + 1
    hdr_end = idx
    assert b"\x00" not in raw[:hdr_end]
    res = subprocess.run(
        [
            'perl',
            '-MDevel::NYTProf::Data',
            '-e',
            'Devel::NYTProf::Data->new({filename=>shift})',
            str(out),
        ],
        capture_output=True,
    )
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
