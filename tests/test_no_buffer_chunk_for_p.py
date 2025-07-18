from tests.conftest import get_chunk_start
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
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b"P"
    length = struct.unpack_from("<I", data, idx+1)[0]
    assert length == 16
    pid_bytes = os.getpid().to_bytes(4, "little")
    assert data[idx+5:idx+9] == pid_bytes

