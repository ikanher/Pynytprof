from tests.conftest import get_chunk_start
from pathlib import Path
import sys
import os
import struct
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer

pytestmark = pytest.mark.xfail(reason="legacy outer chunk expectations")


def test_no_buffer_chunk_for_p(tmp_path):
    out = tmp_path / "nytprof.out"
    with Writer(str(out)):
        pass
    data = out.read_bytes()
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b"P"
    pid_bytes = os.getpid().to_bytes(4, "little")
    assert data[idx+1:idx+5] == pid_bytes

