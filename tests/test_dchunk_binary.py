import pytest
pytestmark = pytest.mark.legacy_psfdce
from tests.conftest import get_chunk_start
import os
import subprocess
import sys
from pathlib import Path


def test_dchunk_binary(tmp_path):
    out = tmp_path / 'nytprof.out'
    env = {
        **os.environ,
        'PYNYTPROF_WRITER': 'py',
        'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src'),
    }
    subprocess.check_call(
        [
            sys.executable,
            '-m',
            'pynytprof.tracer',
            '-o',
            str(out),
            'tests/example_script.py',
        ],
        env=env,
    )
    data = out.read_bytes()
    idx = get_chunk_start(data)
    idx += 17  # skip P record
    length = int.from_bytes(data[idx + 1 : idx + 5], 'little')
    idx += 5 + length
    length = int.from_bytes(data[idx + 1 : idx + 5], 'little')
    idx += 5 + length
    assert data[idx : idx + 1] == b'D'
    dlen = int.from_bytes(data[idx + 1 : idx + 5], 'little')
    payload = data[idx + 5 : idx + 5 + dlen]
    assert payload.startswith(b"\x01")
    assert payload.endswith(b"\x00")
    assert dlen > 1

