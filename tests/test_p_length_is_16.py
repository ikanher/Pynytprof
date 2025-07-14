import os
from pathlib import Path
import importlib.util
import struct
import time
import pytest
from pynytprof import tracer
from pynytprof._pywrite import _perl_nv_size


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
    pid = int.from_bytes(data[idx+5:idx+9], "little")
    assert pid == os.getpid()
    nv_size = _perl_nv_size()
    payload = data[idx+5:idx+5+8+nv_size]
    assert len(payload) == 8 + nv_size
    pid2 = int.from_bytes(payload[0:4], "little")
    ppid = int.from_bytes(payload[4:8], "little")
    if nv_size == 8:
        ts = struct.unpack_from("<d", payload, 8)[0]
        assert abs(ts - time.time()) < 1.0
    assert pid2 == os.getpid()
    assert ppid == os.getppid()
