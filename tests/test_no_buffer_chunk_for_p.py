from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_no_buffer_chunk_for_p(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    assert b"\nP\x10\x00\x00\x00" in data
    for i in range(256):
        if i == 0x10:
            continue
        assert b"\nP" + bytes([i]) not in data
