def test_c_writer_chunks(tmp_path):
    import subprocess, sys, os
    from pathlib import Path
    from tests.conftest import get_chunk_start

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
    end = get_chunk_start(data)
    chunks = data[end:]
    tokens = []
    off = 0
    while off < len(chunks):
        tok = chunks[off:off+1]
        tokens.append(tok)
        length = int.from_bytes(chunks[off+1:off+5], 'little')
        off += 5 + length
    assert tokens == [b'F', b'S', b'D', b'C', b'E']
    assert b"A" not in tokens
    assert data.endswith(b"E\x00\x00\x00\x00")
    f_pos = chunks.index(b"F")
    fid = int.from_bytes(chunks[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(chunks[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and (flags & 0x10)
