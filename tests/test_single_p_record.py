from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_single_p_record(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    assert data.count(b"P\x10\x00\x00\x00") == 1
