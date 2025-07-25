import pytest
pytestmark = pytest.mark.legacy_psfdce
from tests.conftest import get_chunk_start
import os, subprocess, sys
from pathlib import Path


def test_S_payload_free_of_newlines(tmp_path):
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
    # expect S tag
    assert data[idx:idx+1]==b'S'
    slen = int.from_bytes(data[idx+1:idx+5],'little')
    spayload = data[idx+5:idx+5+slen]
    assert b'\n' not in spayload, "S payload contains newline"

