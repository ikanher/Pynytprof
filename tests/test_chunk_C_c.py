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
    cutoff = data.index(b"\nP") + 1
    tokens = []
    off = cutoff
    while off < len(data):
        tok = data[off:off+1]
        tokens.append(tok)
        if tok == b"P":
            if data[off+1:off+5] == b"\x10\x00\x00\x00":
                off += 5 + 16
            else:
                off += 1 + 16
            continue
        length = int.from_bytes(data[off+1:off+5], "little")
        off += 5 + length
    assert b"C" in tokens
