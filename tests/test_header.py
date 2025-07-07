import subprocess
import struct
import os

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
    out = tmp_path / "nytprof.out"
    hdr = out.read_bytes()
    assert hdr[:8] == _MAGIC
    assert hdr[8:16] == b"\x05\x00\x00\x00\x00\x00\x00\x00"
    assert b"\n\n" in hdr
    assert b"\0" not in hdr[16:128]


def test_nytprofhtml(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        with Writer("nytprof.out"):
            pass
    finally:
        os.chdir(cwd)
    out = tmp_path / "nytprof.out"
    subprocess.run([
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "exit 0",
        str(out),
    ], check=True)
