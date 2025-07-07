import os
import struct
import subprocess

import pytest

from pynytprof.writer import Writer, _MAGIC, _MAJOR, _MINOR


def test_header_format(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with Writer("nytprof.out"):
            pass
    finally:
        os.chdir(cwd)
    hdr = (tmp_path / "nytprof.out").read_bytes()[:64]
    expected = _MAGIC + struct.pack("<II", _MAJOR, _MINOR)
    assert hdr.startswith(expected)
    assert b"file=" in hdr and b"\nfile=" not in hdr[20:24]
    assert b"\x00" not in hdr[16:]
    subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data->new(shift)",
            "nytprof.out",
        ],
        cwd=tmp_path,
        check=True,
    )


def test_nytprofhtml(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with Writer("nytprof.out"):
            pass
    finally:
        os.chdir(cwd)
    subprocess.run(
        ["nytprofhtml", "-f", "nytprof.out", "-o", "/tmp/r"],
        cwd=tmp_path,
        check=True,
    )
