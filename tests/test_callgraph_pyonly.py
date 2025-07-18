import os
import sys
import subprocess
import struct
from pathlib import Path
from tests.conftest import get_chunk_start


def test_callgraph_py(tmp_path):
    script = tmp_path / "t.py"
    script.write_text("def foo():\n    bar()\n\ndef bar():\n    pass\n\nfoo()\n")
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYNTP_FORCE_PY": "1",
        "PYNYTPROF_WRITER": "py",
    }
    out = tmp_path / "out.nyt"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), str(script)], env=env
    )
    data = out.read_bytes()
    start = get_chunk_start(data)
    off = start + 21
    d_pos = data.index(b"D", off)
    d_len = struct.unpack_from("<I", data, d_pos + 1)[0]
    assert d_len >= 1
    c_pos = data.index(b"C", d_pos)
    c_len = struct.unpack_from("<I", data, c_pos + 1)[0]
    rec_size = struct.calcsize("<IIIQQ")
    assert c_len % rec_size == 0

