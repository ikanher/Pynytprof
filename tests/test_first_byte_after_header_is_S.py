import struct
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof.reader import header_scan
from tests.utils import run_tracer


def test_first_byte_after_header_is_new_fid(tmp_path):
    out = run_tracer(tmp_path)
    data = out.read_bytes()
    off = header_scan(data)[2]
    assert data[off:off+1] == b'@'
