import os
from pathlib import Path
import importlib.util
import struct
import pytest
from pynytprof import tracer


@pytest.mark.parametrize("writer", ["py", "c"])
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
    assert data[idx+1:idx+5] == (16).to_bytes(4, "little")
    payload = data[idx+5:idx+21]
    assert len(payload) == 16
    pid, ppid, ts = struct.unpack("<IId", payload)
    assert pid == os.getpid()
