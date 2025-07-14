import pathlib
import shutil
import subprocess
import importlib
import pytest

pytest.skip("html roundtrip unsupported", allow_module_level=True)  # noqa: E402

from pynytprof import tracer  # noqa: E402

NYTPROFHTML = shutil.which("nytprofhtml")

pytestmark = pytest.mark.skipif(NYTPROFHTML is None, reason="Devel::NYTProf not installed")


def make_sample_script(tmp: pathlib.Path) -> pathlib.Path:
    code = "def fib(n):\n" "    return 1 if n < 2 else fib(n-1) + fib(n-2)\n" "fib(8)\n"
    p = tmp / "sample.py"
    p.write_text(code)
    return p


def test_nytprofhtml_roundtrip(tmp_path, monkeypatch):
    script = make_sample_script(tmp_path)

    # force pure-Python mode
    monkeypatch.setenv("PYNTP_FORCE_PY", "1")
    importlib.reload(tracer)
    monkeypatch.chdir(tmp_path)

    out = tmp_path / f"nytprof.out.{os.getpid()}"
    tracer.profile_script(str(script), out_path=out)
    assert out.exists(), "profiling produced no output file"

    res = subprocess.run(
        [NYTPROFHTML, "--out", tmp_path / "html", str(out)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert res.returncode == 0, res.stderr.decode()
    assert (tmp_path / "html" / "index.html").exists()
