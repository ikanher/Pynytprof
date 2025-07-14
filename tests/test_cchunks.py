import os
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.mark.parametrize("use_c", [False])
def test_c_chunks(tmp_path, use_c):
    script = Path(__file__).with_name("cg_example.py")
    try:
        import pynytprof._ctrace  # type: ignore  # noqa: F401
    except Exception:
        pytest.skip("_ctrace missing")
    if use_c:
        try:
            import pynytprof._cwrite  # type: ignore  # noqa: F401
        except Exception:
            pytest.skip("_cwrite missing")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if not use_c:
        fake = tmp_path / "fake"
        pkg = fake / "pynytprof"
        pkg.mkdir(parents=True)
        (pkg / "_cwrite.py").write_text("raise ImportError\n")
        env["PYTHONPATH"] = str(fake) + os.pathsep + env["PYTHONPATH"]
    subprocess.check_call([
        sys.executable,
        "-m",
        "pynytprof.tracer",
        str(script),
    ], cwd=tmp_path, env=env)
    data = (tmp_path / "nytprof.out").read_bytes()
    assert b"C\x00" in data
    assert b"D\x00" in data
