import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mmap
import struct
import zlib
import shutil
import pytest
from pynytprof.writer import Writer, _SubStats




def run_profile(tmp_path):
    out = tmp_path / "out.nyt"
    with Writer(str(out)) as w:
        fid = w.add_file("script.py", True)
        foo = w.sub_table.add(fid, 1, 5, "foo", "m")
        bar = w.sub_table.add(fid, 1, 2, "bar", "m")
        for _ in range(5):
            w.stats_map.setdefault(bar, _SubStats()).update(10, 0)
            w.stats_map.setdefault(foo, _SubStats()).update(20, 10)
    return out


def parse_a_chunk(path: Path):
    with path.open("rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        hdr_end = 0
        for _ in range(10):
            hdr_end = mm.find(b"\n", hdr_end) + 1
        off = hdr_end
        while off < mm.size():
            tag = mm[off:off+1]
            length = struct.unpack_from("<I", mm, off+1)[0]
            off += 5
            payload = mm[off:off+length]
            off += length
            if tag == b"A":
                payload = zlib.decompress(payload)
                mm.close()
                return struct.unpack_from("<IIQQI", payload, 0)
        mm.close()
    return None


def test_sub_attr_chunk(tmp_path):
    out = run_profile(tmp_path)
    rec = parse_a_chunk(out)
    assert rec is not None
    _, calls, incl, excl, _ = rec
    assert calls == 5
    assert incl >= excl


def test_perl_sub_attr(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    out = run_profile(tmp_path)
    cmd = [
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "print Devel::NYTProf::Data->new({filename=>shift})->subs->[0]->calls",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    assert res.stdout.strip() == "5"
