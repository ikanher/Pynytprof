from tests.conftest import get_chunk_start
import os
from pathlib import Path
import importlib.util
import struct
import pytest
from pynytprof import tracer


@pytest.mark.parametrize("writer", ["py"])
def test_p_payload_is_16_bytes(tmp_path, writer):
    env = os.environ.copy()
    env["PYNYTPROF_WRITER"] = writer
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if writer == "c" and importlib.util.find_spec("pynytprof._cwrite") is None:
        pytest.skip("_cwrite missing")
    out = tmp_path / "nytprof.out"
    monkeypatch = pytest.MonkeyPatch()
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    tracer.profile_command("pass", out_path=out)
    monkeypatch.undo()
    data = out.read_bytes()
    idx = get_chunk_start(data)
    assert data[idx:idx+1] == b"P"
    payload = data[idx+1:idx+17]
    pid2, ppid, ts = struct.unpack("<IId", payload)
    assert len(payload) == 16
    assert pid2 == os.getpid()
    assert ppid == os.getppid()

