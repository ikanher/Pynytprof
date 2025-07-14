from pathlib import Path
import sys
import os
import struct
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_no_buffer_chunk_for_p(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    pid_first = struct.pack("<I", os.getpid())[:1]
    length16 = (16).to_bytes(4, "little")
    assert b"\nP" + length16 + pid_first in data
    for i in range(256):
        if i == pid_first[0]:
            continue
        assert b"\nP" + length16 + bytes([i]) not in data
