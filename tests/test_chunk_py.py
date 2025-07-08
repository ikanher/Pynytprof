from pathlib import Path, PurePosixPath
import subprocess, os, sys


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
    assert data.count(b"F") == 1
    assert b"A" not in data
    end = data.index(b"\n", data.rfind(b"!evals=0"))
    chunks = data[end + 1 :]
    token = chunks[:1]
    length = int.from_bytes(chunks[1:5], "little")
    assert token == b"F"
    f_pos = chunks.index(b"F")
    fid = int.from_bytes(chunks[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(chunks[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and flags & 0x10
    assert data.endswith(b"E\x00\x00\x00\x00")
