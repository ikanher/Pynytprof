from pathlib import Path, PurePosixPath
import subprocess, os, sys, struct


def test_py_writer_chunks(tmp_path):
    out = tmp_path / "p.out"
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", "-o", str(out), "-e", "pass"],
        env={
            **os.environ,
            "PYNYTPROF_WRITER": "py",
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
        length = int.from_bytes(chunks[off+1:off+5], "little")
        off += 5 + length
    assert tokens == [b"P", b"F", b"S", b"E"]
    assert b"A" not in tokens
    f_pos = chunks.index(b"F")
    fid = int.from_bytes(chunks[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(chunks[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and flags & 0x10
    flen = int.from_bytes(chunks[f_pos + 1 : f_pos + 5], "little")
    script_path = Path(__file__).resolve().parents[1] / "src" / "pynytprof" / "tracer.py"
    st = script_path.stat()
    payload = (
        struct.pack("<IIII", 0, 0x10, st.st_size, int(st.st_mtime))
        + str(script_path).encode()
        + b"\0"
    )
    assert flen == len(payload)
    assert data.endswith(b"E\x00\x00\x00\x00")
