import subprocess
import struct

import pytest

from pynytprof.writer import Writer, _MAGIC, _MAJOR, _MINOR


def test_binary_header(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)):
        pass
    data = out.read_bytes()[:32]
    expected = _MAGIC + struct.pack("<II", _MAJOR, _MINOR)
    assert data.startswith(expected)
    assert data[16:21] == b"file="
    res = subprocess.run([
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "exit 0",
        str(out),
    ])
    assert res.returncode == 0
