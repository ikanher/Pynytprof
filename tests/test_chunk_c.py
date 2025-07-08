def test_c_writer_chunks(tmp_path):
    import subprocess, sys, os

    out = tmp_path / "c.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env={**os.environ, "PYNYTPROF_WRITER": "c"},
    )
    data = out.read_bytes()
    assert data.startswith(b"NYTProf 5 0\n")
    assert data.endswith(b"E\x00\x00\x00\x00")
    f_pos = data.index(b"F")
    plen = int.from_bytes(data[f_pos + 1 : f_pos + 5], "little")
    fid = int.from_bytes(data[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(data[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and (flags & 0x10)
