import subprocess, sys, os, struct
from pathlib import Path


def test_schunk(tmp_path):
    out = tmp_path / "out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "tests/example_script.py"],
        env=env,
    )
    data = out.read_bytes()
    s_pos = data.index(b"S")
    slen = struct.unpack_from("<I", data, s_pos + 1)[0]
    assert slen % 28 == 0 and slen > 0
