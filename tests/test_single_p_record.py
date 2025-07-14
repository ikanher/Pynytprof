from pathlib import Path
import sys
import os
import struct
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


def test_single_p_record(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    length16 = (16).to_bytes(4, "little")
    occurrences = [i for i in range(len(data) - 5) if data[i : i + 5] == b"P" + length16]
    assert len(occurrences) == 1
