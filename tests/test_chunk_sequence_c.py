def test_c_writer_chunk_sequence(tmp_path):
    import subprocess, sys, os
    from pathlib import Path
    out = tmp_path / "nytprof.out"
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    subprocess.check_call([sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"], env=env)
    data = out.read_bytes()
    cutoff = data.index(b"\n\nP") + 2
    tokens = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        tokens.append(tok)
        if tok == b"P":
            off += 1 + 4 + 4 + 8
            continue
        length = int.from_bytes(data[off+1:off+5], "little")
        off += 5 + length
    assert tokens == [b'P', b'S', b'D', b'C', b'E']

