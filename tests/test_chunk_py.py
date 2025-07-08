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
    first = data.split(b"\n\n", 1)[1]
    token = first[:1]
    length = int.from_bytes(first[1:5], "little")
    assert token == b"F"
    f_pos = data.index(b"F")
    f_len = int.from_bytes(data[f_pos + 1 : f_pos + 5], "little")
    fid = int.from_bytes(data[f_pos + 5 : f_pos + 9], "little")
    flags = int.from_bytes(data[f_pos + 9 : f_pos + 13], "little")
    assert fid == 0 and flags & 0x10
    assert data.endswith(b"E\x00\x00\x00\x00")
