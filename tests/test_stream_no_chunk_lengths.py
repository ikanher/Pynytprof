import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer
from pynytprof.reader import header_scan


def test_stream_no_chunk_lengths(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    _, _, off = header_scan(data)
    # After first token expect varint prefix, not 4-byte length
    first_tag = data[off]
    assert first_tag in {1, 2, ord('@'), ord('S'), ord('F'), ord('D'), ord('C'), ord('+'), ord('p')}
    next_bytes = data[off + 1 : off + 5]
    assert next_bytes != struct.pack('<I', len(data))  # not a length marker

