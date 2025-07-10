def test_c_writer_emits_C_chunk(tmp_path):
    import subprocess, sys, os
    from pathlib import Path
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "c",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env)
    data = out.read_bytes()
    cutoff = data.index(b"\n\n") + 2
    tokens = []
    off = cutoff
    while off < len(data):
        tokens.append(data[off:off+1])
        length = int.from_bytes(data[off+1:off+5], "little")
        off += 5 + length
    assert b"C" in tokens
