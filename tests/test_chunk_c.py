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
    assert data.startswith(b"NYTProf 5 0\n")
    assert data.endswith(b"E\x00\x00\x00\x00")
    assert data.count(b"F") == 1
    assert b"A" not in data
    end = data.index(b"\n", data.rfind(b"!evals=0"))
    chunks = data[end + 1 :]
    f_pos = chunks.index(b"F")
    fid = int.from_bytes(chunks[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(chunks[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and (flags & 0x10)
