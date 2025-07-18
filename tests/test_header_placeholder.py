def test_no_size_placeholder(tmp_path):
    import os, subprocess, sys, re
    from pathlib import Path

    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    out = tmp_path / "nytprof.out"
    subprocess.check_call([sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env)
    data = out.read_bytes()
    header = data.split(b"\nP", 1)[0]
    assert b"{SIZE" not in header
