import pytest
pytestmark = pytest.mark.legacy_psfdce
from pathlib import Path
import subprocess
import sys
import time
import os
import struct

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof.reader import read, _MAGIC as PREFIX, _MAJOR, _MINOR


import pytest


@pytest.mark.parametrize("hide_cwrite", [False, True])
def test_format(tmp_path, hide_cwrite):
    script = Path(__file__).with_name("example_script.py")
    out = tmp_path / f"nytprof.out.{os.getpid()}"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    if hide_cwrite:
        fake = tmp_path / "fake"
        pkg = fake / "pynytprof"
        pkg.mkdir(parents=True)
        (pkg / "_cwrite.py").write_text("raise ImportError\n")
        env["PYTHONPATH"] = str(fake) + os.pathsep + env["PYTHONPATH"]
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), str(script)],
        cwd=tmp_path,
        env=env,
    )
    assert out.exists()
    with out.open("rb") as f:
        prefix = f.read(16)
        assert prefix.startswith(b"NYTProf")
    hdr = out.read_bytes()[:32]
    assert hdr.startswith(b"NYTProf")
    start = time.perf_counter()
    data = read(str(out))

    assert data["header"][0] == 5
    assert data["attrs"].get("ticks_per_sec") == 10_000_000
    assert data["records"]
    line_numbers = [r[1] for r in data["records"]]
    assert all(num > 0 for num in line_numbers)
    assert line_numbers == sorted(line_numbers)
