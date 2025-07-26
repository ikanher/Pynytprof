import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.reader import header_scan


def test_no_ascii_wrappers(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)) as w:
        w.start_profile()
        w.end_profile()
    data = out.read_bytes()
    _, _, off = header_scan(data)
    assert data[off:off+7] != b'SFDC Ep'
