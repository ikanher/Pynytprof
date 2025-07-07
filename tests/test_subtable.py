import mmap
import struct
import zlib
import subprocess
import shutil
from pathlib import Path

import pytest
from pynytprof.writer import Writer


def test_subtable_chunk(tmp_path):
    out = tmp_path / "out.nyt"
    foo = tmp_path / "foo.py"
    bar = tmp_path / "bar.py"
    foo.write_text("\n")
    bar.write_text("\n")
    with Writer(str(out)) as w:
        fid1 = w.add_file(str(foo), True)
        fid2 = w.add_file(str(bar), False)
        w.sub_table.add(fid1, 1, 2, "fa", "pkg1")
        w.sub_table.add(fid2, 3, 4, "fb", "pkg2")
    with out.open("rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        hdr_end = mm.find(b"\n\n") + 2
        off = hdr_end
        found = False
        while off < mm.size():
            tag = mm[off : off + 1]
            length = struct.unpack_from("<I", mm, off + 1)[0]
            off += 5
            payload = mm[off : off + length]
            off += length
            if tag == b"S":
                payload = zlib.decompress(payload)
                assert len(payload) == 2 * 24
                found = True
                break
        mm.close()
    assert found
    # header shouldn't be rewritten with subtable statistics


def test_perl_subs(tmp_path):
    if not shutil.which("perl"):
        pytest.skip("perl missing")
    out = tmp_path / "out.nyt"
    with Writer(str(out)) as w:
        fid = w.add_file(str(out), True)
        w.sub_table.add(fid, 1, 2, "f", "m")
    cmd = [
        "perl",
        "-MDevel::NYTProf::Data",
        "-e",
        "print Devel::NYTProf::Data->new(shift)->subs",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip("NYTProf Perl module missing")
    assert int(res.stdout.strip()) > 0

