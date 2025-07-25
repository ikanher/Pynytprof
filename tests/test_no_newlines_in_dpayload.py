import pytest
pytestmark = pytest.mark.legacy_psfdce
from tests.conftest import get_chunk_start
import os, subprocess, sys
from pathlib import Path


def test_D_payload_free_of_newlines(tmp_path):
    out = tmp_path/'nytprof.out'
    env = {
        **os.environ,
        "PYNYTPROF_WRITER":"py",
        "PYNYTPROF_DEBUG":"1",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]/"src"),
    }
    subprocess.check_call(
        [sys.executable,"-m","pynytprof.tracer","-o",str(out),"-e","pass"],
        env=env
    )
    data = out.read_bytes()
    idx = get_chunk_start(data)
    idx += 17  # skip P
    # skip S
    slen = int.from_bytes(data[idx+1:idx+5],'little')
    idx += 5 + slen
    flen = int.from_bytes(data[idx+1:idx+5],'little')
    idx += 5 + flen
    # expect D
    assert data[idx:idx+1]==b'D'
    dlen = int.from_bytes(data[idx+1:idx+5],'little')
    dpayload = data[idx+5:idx+5+dlen]
    assert dpayload.endswith(b"\x00")

