import os
import subprocess
from pathlib import Path
import shutil
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pynytprof._pywrite import Writer


def _perl_available() -> bool:
    if not shutil.which("perl"):
        return False
    try:
        subprocess.run([
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return False
    return True


@pytest.mark.skipif(not _perl_available(), reason="NYTProf not installed")
def test_minimal_profile_roundtrip(tmp_path: Path):
    p = tmp_path / "nytprof.out.test"
    with p.open("wb") as fh:
        w = Writer(fh)
        w.start_profile()
        w.add_file(
            fid=1,
            name="test.pl",
            size=1,
            mtime=0,
            flags=0,
            eval_fid=0,
            eval_line=0,
        )
        w.add_src_line(fid=1, line=1, text="1;")
        w.write_time_line(fid=1, line=1, elapsed=-11, overflow=0)
        w.end_profile()

    subprocess.run(
        [
            "perl",
            "-MDevel::NYTProf::Data",
            "-e",
            "Devel::NYTProf::Data->new({filename=>shift,quiet=>1})",
            str(p),
        ],
        check=True,
    )


def test_no_ascii_chunk_bytes(tmp_path: Path):
    p = tmp_path / "nytprof.out.test"
    with p.open("wb") as fh:
        w = Writer(fh)
        w.start_profile()
        w.add_file(
            fid=1,
            name="x.pl",
            size=1,
            mtime=0,
            flags=0,
            eval_fid=0,
            eval_line=0,
        )
        w.add_src_line(fid=1, line=1, text="1;")
        w.write_time_line(fid=1, line=1, elapsed=-11, overflow=0)
        w.end_profile()

    data = p.read_bytes()
    hdr_end = data.index(b"\nP")
    off = hdr_end + 1
    # P record length is 17 bytes
    off_after_p = off + 17
    assert data[off_after_p] not in b"SFDCE"
