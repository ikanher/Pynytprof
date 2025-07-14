import os
import subprocess
import sys
from pathlib import Path
import shutil
import struct
import zlib
import pytest


@pytest.mark.parametrize("use_c", [True, False])
def test_callgraph(tmp_path, use_c):
    script = Path(__file__).with_name("cg_example.py")
    if not shutil.which("nytprofhtml"):
        pytest.skip("nytprofhtml missing")
    try:
        import pynytprof._ctrace  # type: ignore  # noqa: F401
    except Exception:
        pytest.skip("_ctrace missing")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if not use_c:
        fake = tmp_path / "fake"
        pkg = fake / "pynytprof"
        pkg.mkdir(parents=True)
        (pkg / "_cwrite.py").write_text("raise ImportError\n")
        env["PYTHONPATH"] = str(fake) + os.pathsep + env["PYTHONPATH"]
    out = tmp_path / f"nytprof.out.{os.getpid()}"
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        "-o",
        str(out),
        str(script),
    ], cwd=tmp_path, env=env)
    data = out.read_bytes()
    off = data.index(b"C")
    clen = int.from_bytes(data[off + 1 : off + 5], "little")
    payload = data[off + 5 : off + 5 + clen]
    payload = zlib.decompress(payload)
    rec = struct.unpack_from("<IIIQQ", payload, 0)
    assert rec[3] > 0
    try:
        subprocess.check_call(["nytprofhtml", "-f", out.name], cwd=tmp_path)
    except Exception:
        with open(out, "rb") as fh:
            print("HDR", fh.read(25).hex(), file=sys.stderr)
        raise
    html = (tmp_path / "nytprof" / "index.html").read_text()
    assert "cg_example.py->foo" in html
