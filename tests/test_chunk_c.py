def test_c_writer_chunks(tmp_path):
    import subprocess, sys, os
    from pathlib import Path

    out = tmp_path / "c.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env={
            **os.environ,
            "PYNYTPROF_WRITER": "c",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        },
    )
    data = out.read_bytes()
    end = data.index(b"\n", data.rfind(b"!evals=0"))
    chunks = data[end + 1 :]
    tokens = []
    off = 0
    while off < len(chunks):
        tok = chunks[off:off+1]
        tokens.append(tok)
        length = int.from_bytes(chunks[off+1:off+5], 'little')
        off += 5 + length
    assert tokens.count(b'P') == 1
    assert tokens.count(b'F') == 1
    assert b"A" not in tokens
    assert data.endswith(b"E\x00\x00\x00\x00")
    f_pos = chunks.index(b"F")
    fid = int.from_bytes(chunks[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(chunks[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and (flags & 0x10)
