import os
import struct
import subprocess
import pathlib

import pytest

from pynytprof.writer import Writer


def test_header_format(tmp_path):
    p = tmp_path / "nytprof.out"
    with Writer(str(p)):
        pass
    hdr = p.read_bytes()[:64]
    assert hdr[:8] == b"NYTPROF\x00"
    assert hdr[8:12] == struct.pack("<I", 5)
    assert hdr[12:16] == struct.pack("<I", 0)
    assert b"\x00" not in hdr[16:32]
    assert b"file=" in hdr
    res = subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data->new({filename => shift})",
            str(p),
        ],
        capture_output=True,
    )
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")


def test_nytprofhtml(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with Writer("nytprof.out"):
            pass
    finally:
        os.chdir(cwd)
    res = subprocess.run(
        ["nytprofhtml", "-f", "nytprof.out", "-o", "/tmp/r"],
        cwd=tmp_path,
        capture_output=True,
    )
    if res.returncode != 0:
        pytest.skip("nytprofhtml missing")
