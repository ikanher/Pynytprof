import os
from pathlib import Path
import importlib.util
import struct
import pytest
from pynytprof import tracer


@pytest.mark.parametrize("writer", ["py"])
def test_p_length_is_16(tmp_path, writer):
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
    idx = data.index(b"\nP") + 1
    assert data[idx:idx+1] == b"P"
    pid = int.from_bytes(data[idx+1:idx+5], "little")
    assert pid == os.getpid()
    payload = data[idx+1:idx+17]
    assert len(payload) == 16
    pid2, ppid, ts = struct.unpack("<IId", payload)
    assert pid2 == os.getpid()
    assert ppid == os.getppid()

